"""Comparative experiment of the TCC (section 6.5): emission vs distance criterion.

For each instance, runs the GA with the distance and the emission criterion under each seed,
evaluates both routes with the MEET model and computes
    delta = (E_distance - E_emission) / E_distance * 100
The experiment passes when the mean delta is at least 5% in at least 4 of the 5 instances.

Instances are JSON files in the POST /optimize request format (criterion and seed are ignored),
one per file in --instances-dir. Without it, synthetic instances are generated around central
Sao Paulo so the experiment can run before the OSM instances are exported.

    python -m experiments.run_experiment --output-dir experiments/resultados
"""

import argparse
import csv
import itertools
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.main import app
from app.models.chromosome import Chromosome
from app.optimization.fitness.emission import SegmentEmissionFitnessFunction
from app.optimization.route_optimizer import GaParameters, Leg, build_matrices, optimize_route

INSTANCE_SIZES = (10, 15, 20, 25, 30)
SEEDS = (1, 2, 3)
API_GA_PARAMETERS = GaParameters(population_size=300, generations=500, crossover_rate=0.9, mutation_rate=0.4)
RANDOM_SAMPLES = 1000
RANDOM_BASELINE_STREAM = 7_919
RANDOM_TARGET_RATIO = 0.9
DELTA_TARGET_PERCENT = 5.0
INSTANCES_REQUIRED = 4
VEHICLE_MASS_KG = 7_500.0

# Bounding box of central Sao Paulo (Se, Republica, Bela Vista, Liberdade, Consolacao).
LAT_RANGE = (-23.565, -23.535)
LON_RANGE = (-46.665, -46.625)
ELEVATION_RANGE_M = (720.0, 820.0)
SPEED_RANGE_KMH = (15.0, 50.0)
MAX_SLOPE_PERCENT = 8.0


@dataclass(frozen=True)
class Instance:
    name: str
    point_count: int
    vehicle_mass_kg: float
    load_ratio: float
    legs: list[Leg]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def synthetic_instance(point_count: int, seed: int) -> Instance:
    """Random points with an elevation each, so slope a->b is the negative of slope b->a."""
    rng = np.random.default_rng(seed)
    lat = rng.uniform(*LAT_RANGE, point_count)
    lon = rng.uniform(*LON_RANGE, point_count)
    elevation = rng.uniform(*ELEVATION_RANGE_M, point_count)
    speed = rng.uniform(*SPEED_RANGE_KMH, (point_count, point_count))
    speed = (speed + speed.T) / 2

    legs = []
    for a, b in itertools.permutations(range(point_count), 2):
        distance_km = haversine_km(lat[a], lon[a], lat[b], lon[b])
        slope = (elevation[b] - elevation[a]) / (distance_km * 1000) * 100
        slope = float(np.clip(slope, -MAX_SLOPE_PERCENT, MAX_SLOPE_PERCENT))
        legs.append(Leg(a, b, distance_km, float(speed[a, b]), slope))
    return Instance(f"sintetica-{point_count:02d}", point_count, VEHICLE_MASS_KG, 1.0, legs)


def load_instance(path: Path) -> Instance:
    data = json.loads(path.read_text(encoding="utf-8"))
    legs = [
        Leg(
            s["from_index"], s["to_index"], s["distance_meters"] / 1000,
            s["average_speed_kmh"], s["slope_percent"],
        )
        for s in data["segments"]
    ]
    return Instance(
        path.stem, data["point_count"], data["vehicle_mass_kg"], data.get("load_ratio", 1.0), legs
    )


def random_route_emissions_kg(instance: Instance, seed: int, samples: int = RANDOM_SAMPLES) -> np.ndarray:
    """Emission of each random visiting order, the reference of KPI-6.

    The draws come from a generator of their own, seeded apart from the GA, so adding or changing the
    baseline never changes the GA results of the same seed."""
    distance, speed, slope = build_matrices(instance.point_count, instance.legs)
    fitness = SegmentEmissionFitnessFunction(
        distance, speed, slope, instance.vehicle_mass_kg, return_to_depot=False,
        load_ratio=instance.load_ratio,
    )
    rng = np.random.default_rng([RANDOM_BASELINE_STREAM, seed])
    genes = instance.point_count - 1
    return np.array([fitness.evaluate(Chromosome(rng.permutation(genes))) for _ in range(samples)]) / 1000


def run_instance(instance: Instance, seeds=SEEDS, ga_parameters: GaParameters = API_GA_PARAMETERS) -> list[dict]:
    rows = []
    for seed in seeds:
        runs = {
            criterion: optimize_route(
                criterion, instance.vehicle_mass_kg, instance.point_count, instance.legs,
                load_ratio=instance.load_ratio, seed=seed, ga_parameters=ga_parameters,
            )
            for criterion in ("distance", "emission")
        }
        random_kg = random_route_emissions_kg(instance, seed)
        e_distance = runs["distance"].total_emission_g / 1000
        e_emission = runs["emission"].total_emission_g / 1000
        rows.append(
            {
                "instance": instance.name,
                "points": instance.point_count,
                "seed": seed,
                "e_distance_kg": e_distance,
                "e_emission_kg": e_emission,
                "e_random_kg": float(random_kg.mean()),
                "e_random_std_kg": float(random_kg.std()),
                "e_random_min_kg": float(random_kg.min()),
                "e_random_max_kg": float(random_kg.max()),
                "random_samples": len(random_kg),
                "ratio_to_random": e_emission / float(random_kg.mean()),
                "delta_percent": (e_distance - e_emission) / e_distance * 100 if e_distance else 0.0,
                "km_distance_route": runs["distance"].total_distance_km,
                "km_emission_route": runs["emission"].total_distance_km,
                "seconds_distance": runs["distance"].elapsed_s,
                "seconds_emission": runs["emission"].elapsed_s,
                "generations_emission": runs["emission"].generations,
                "converged_at_emission": runs["emission"].converged_at_generation,
                "sequence_distance": runs["distance"].sequence,
                "sequence_emission": runs["emission"].sequence,
                "history_emission": runs["emission"].best_fitness_history,
                "history_distance": runs["distance"].best_fitness_history,
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    instances = []
    for name in dict.fromkeys(r["instance"] for r in rows):
        group = [r for r in rows if r["instance"] == name]
        mean_delta = float(np.mean([r["delta_percent"] for r in group]))
        instances.append(
            {
                "instance": name,
                "points": group[0]["points"],
                "mean_e_distance_kg": float(np.mean([r["e_distance_kg"] for r in group])),
                "mean_e_emission_kg": float(np.mean([r["e_emission_kg"] for r in group])),
                "mean_delta_percent": mean_delta,
                "std_delta_percent": float(np.std([r["delta_percent"] for r in group])),
                "max_seconds": max(max(r["seconds_distance"], r["seconds_emission"]) for r in group),
                "mean_ratio_to_random": float(np.mean([r["ratio_to_random"] for r in group])),
                "meets_random_target": float(np.mean([r["ratio_to_random"] for r in group])) <= RANDOM_TARGET_RATIO,
                "meets_target": mean_delta >= DELTA_TARGET_PERCENT,
            }
        )
    passed = sum(i["meets_target"] for i in instances)
    return {
        "optimizer_version": app.version,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "delta_target_percent": DELTA_TARGET_PERCENT,
        "instances_meeting_target": passed,
        "experiment_passes": passed >= INSTANCES_REQUIRED,
        "all_under_60_seconds": all(i["max_seconds"] < 60 for i in instances),
        "instances": instances,
    }


def write_results(rows: list[dict], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "execucoes.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [k for k in rows[0] if not k.startswith(("sequence", "history"))]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "execucoes.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output_dir / "resumo.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--instances-dir", type=Path, help="folder with *.json instances in the /optimize format")
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/resultados"))
    parser.add_argument("--population", type=int, default=API_GA_PARAMETERS.population_size)
    parser.add_argument("--generations", type=int, default=API_GA_PARAMETERS.generations)
    parser.add_argument("--crossover", type=float, default=API_GA_PARAMETERS.crossover_rate)
    parser.add_argument("--mutation", type=float, default=API_GA_PARAMETERS.mutation_rate)
    args = parser.parse_args(argv)
    ga_parameters = GaParameters(args.population, args.generations, args.crossover, args.mutation)

    if args.instances_dir:
        instances = [load_instance(p) for p in sorted(args.instances_dir.glob("*.json"))]
    else:
        instances = [synthetic_instance(n, seed=n) for n in INSTANCE_SIZES]

    rows = [row for instance in instances for row in run_instance(instance, ga_parameters=ga_parameters)]
    summary = summarize(rows)
    write_results(rows, summary, args.output_dir)

    for i in summary["instances"]:
        mark = "ok" if i["meets_target"] else "--"
        print(f"{mark} {i['instance']:<16} delta medio {i['mean_delta_percent']:6.2f}%  max {i['max_seconds']:.1f}s")
    print(
        f"{summary['instances_meeting_target']}/{len(summary['instances'])} instancias com delta >= "
        f"{DELTA_TARGET_PERCENT}%: experimento {'APROVADO' if summary['experiment_passes'] else 'REPROVADO'}"
    )
    return summary


if __name__ == "__main__":
    main()
