"""Reference solutions for the synthetic instances of the TCC experiment (item L03).

For each of the five instances and each criterion (emission and distance), computes:
  - nearest neighbour from the depot followed by 2-opt until no move improves the route;
  - for the 10-point instance, the exact optimum, by evaluating every visiting order (9! = 362,880).

The leg costs are the same matrices the genetic algorithm uses: emission from the MEET model
(SegmentEmissionFitnessFunction) and straight-line distance, open route starting at the depot.
The table compares them with the GA runs already in the repository (default configuration of
2026-11-07 and the 2,000-generation run of the TCC).

    python -m experiments.reference_heuristics --output-dir experiments/resultados-referencia-AAAA-MM-DD
"""

import argparse
import itertools
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.optimization.fitness.emission import SegmentEmissionFitnessFunction
from app.optimization.route_optimizer import build_matrices
from experiments.run_experiment import INSTANCE_SIZES, Instance, synthetic_instance

GA_RUNS = {
    "ag_padrao": Path("experiments/resultados-padrao-2026-11-07/execucoes.json"),
    "ag_2000": Path("experiments/resultados-tcc-2000/execucoes.json"),
}
EXACT_MAX_POINTS = 10


def cost_matrices(instance: Instance) -> dict[str, np.ndarray]:
    distance, speed, slope = build_matrices(instance.point_count, instance.legs)
    emission = SegmentEmissionFitnessFunction(
        distance, speed, slope, instance.vehicle_mass_kg, return_to_depot=False, load_ratio=instance.load_ratio,
    )
    return {"emission": emission.emission_matrix_g / 1000, "distance": distance}


def route_cost(cost: np.ndarray, route: list[int]) -> float:
    return float(sum(cost[a, b] for a, b in zip(route, route[1:])))


def nearest_neighbour(cost: np.ndarray) -> list[int]:
    route, left = [0], set(range(1, len(cost)))
    while left:
        nxt = min(left, key=lambda b: (cost[route[-1], b], b))
        route.append(nxt)
        left.remove(nxt)
    return route


def two_opt(cost: np.ndarray, route: list[int]) -> tuple[list[int], int]:
    """Reverses route[i..j] (never the depot) while some reversal lowers the cost; first improvement.

    The costs are asymmetric (slope and speed depend on the direction), so each candidate is
    evaluated on the whole route instead of by the four changed edges."""
    best, best_cost, moves = list(route), route_cost(cost, route), 0
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                candidate_cost = route_cost(cost, candidate)
                if candidate_cost < best_cost - 1e-12:
                    best, best_cost, moves, improved = candidate, candidate_cost, moves + 1, True
                    break
            if improved:
                break
    return best, moves


def exact_optimum(cost: np.ndarray) -> tuple[list[int], int]:
    """Evaluates every order of the points 1..n-1 after the depot, in chunks, and returns the cheapest."""
    n = len(cost)
    best_cost, best_route, evaluated = math.inf, None, 0
    orders = itertools.permutations(range(1, n))
    while True:
        chunk = np.array(list(itertools.islice(orders, 200_000)), dtype=np.int64)
        if not len(chunk):
            break
        routes = np.hstack([np.zeros((len(chunk), 1), dtype=np.int64), chunk])
        totals = cost[routes[:, :-1], routes[:, 1:]].sum(axis=1)
        k = int(np.argmin(totals))
        if totals[k] < best_cost:
            best_cost, best_route = float(totals[k]), routes[k].tolist()
        evaluated += len(chunk)
    return best_route, evaluated


def ga_results() -> dict[str, dict[str, dict[str, float]]]:
    """Best and mean over the three seeds, per GA run and instance: emission route (kg) and distance route (km)."""
    results = {}
    for label, path in GA_RUNS.items():
        rows = json.loads(path.read_text(encoding="utf-8"))
        per_instance = {}
        for row in rows:
            entry = per_instance.setdefault(row["instance"], {"emission": [], "distance": []})
            entry["emission"].append(row["e_emission_kg"])
            entry["distance"].append(row["km_distance_route"])
        results[label] = {
            name: {f"{criterion}_{stat}": float(fn(values)) for criterion, values in entry.items()
                   for stat, fn in (("min", min), ("mean", np.mean))}
            for name, entry in per_instance.items()
        }
    return results


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    ga = ga_results()
    rows = []
    for n in INSTANCE_SIZES:
        instance = synthetic_instance(n, seed=n)
        costs = cost_matrices(instance)
        for criterion, cost in costs.items():
            other = costs["distance" if criterion == "emission" else "emission"]
            started = time.perf_counter()
            nn = nearest_neighbour(cost)
            improved, moves = two_opt(cost, nn)
            heuristic_s = time.perf_counter() - started
            row = {
                "instance": instance.name,
                "points": n,
                "criterion": criterion,
                "unit": "kg CO2" if criterion == "emission" else "km",
                "nearest_neighbour": route_cost(cost, nn),
                "nn_2opt": route_cost(cost, improved),
                "nn_2opt_moves": moves,
                "nn_2opt_seconds": heuristic_s,
                "nn_2opt_route": improved,
                "nn_2opt_other_criterion": route_cost(other, improved),
            }
            if n <= EXACT_MAX_POINTS:
                started = time.perf_counter()
                optimum, evaluated = exact_optimum(cost)
                row.update({
                    "exact": route_cost(cost, optimum),
                    "exact_route": optimum,
                    "exact_orders_evaluated": evaluated,
                    "exact_seconds": time.perf_counter() - started,
                    "exact_other_criterion": route_cost(other, optimum),
                })
            for label, per_instance in ga.items():
                values = per_instance.get(instance.name)
                if values:
                    row[f"{label}_min"] = values[f"{criterion}_min"]
                    row[f"{label}_mean"] = values[f"{criterion}_mean"]
            rows.append(row)
            print(f"{instance.name} {criterion:<8} NN {row['nearest_neighbour']:.4f}  NN+2opt {row['nn_2opt']:.4f}"
                  + (f"  exato {row['exact']:.4f}" if "exact" in row else "")
                  + f"  AG padrão (melhor/média) {row.get('ag_padrao_min', float('nan')):.4f}/{row.get('ag_padrao_mean', float('nan')):.4f}"
                  + f"  AG 2.000 {row.get('ag_2000_min', float('nan')):.4f}/{row.get('ag_2000_mean', float('nan')):.4f}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "instances": "synthetic_instance(n, seed=n) for n in " + str(list(INSTANCE_SIZES)),
        "ga_runs": {label: str(path) for label, path in GA_RUNS.items()},
    }
    (args.output_dir / "referencias.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=2), encoding="utf-8")
    columns = [c for c in rows[0] if not c.endswith("_route")] + [c for c in rows[-1] if c not in rows[0] and not c.endswith("_route")]
    columns = list(dict.fromkeys(columns + ["exact", "exact_orders_evaluated", "exact_seconds", "exact_other_criterion"]))
    lines = [",".join(columns)] + [",".join("" if r.get(c) is None else str(r.get(c, "")) for c in columns) for r in rows]
    (args.output_dir / "referencias.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"meta": meta, "rows": rows}


if __name__ == "__main__":
    main()
