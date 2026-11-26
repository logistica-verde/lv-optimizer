"""Reruns the 54 real-road trials of 2026-10-19 from the package, without OSRM, SRTM or the API.

For each trial and criterion, builds the leg matrix from pares.json in the order the API sent the
points (start point first, then the delivery points by id), runs the genetic algorithm with the seed
the API used (RouteProcessor.seedOf) and the parameters of that day, and compares the route with the
one stored in the database (ensaios.json).

    python reproducao/ruas-reais/reproduzir.py            # all 54 trials, about 18 minutes
    python reproducao/ruas-reais/reproduzir.py --trials 1 2
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.optimization.route_optimizer import GaParameters, Leg, optimize_route  # noqa: E402

HERE = Path(__file__).resolve().parent


def legs_for(points: list[int], pairs: dict) -> list[Leg]:
    return [
        Leg(a, b, pairs[(pa, pb)]["distance_meters"] / 1000, pairs[(pa, pb)]["average_speed_kmh"],
            pairs[(pa, pb)]["slope_percent"])
        for a, pa in enumerate(points) for b, pb in enumerate(points) if a != b
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, nargs="*", help="only these trial numbers")
    parser.add_argument("--output", type=Path, help="JSON with every reproduced route")
    args = parser.parse_args(argv)

    package = json.loads((HERE / "ensaios.json").read_text(encoding="utf-8"))
    pairs = {(p["from_point"], p["to_point"]): p for p in json.loads((HERE / "pares.json").read_text(encoding="utf-8"))}
    ga = GaParameters(**package["ga_parameters"])
    trials = [t for t in package["trials"] if not args.trials or t["trial"] in args.trials]

    results, same = [], 0
    for trial in trials:
        points = trial["points_sent"]
        legs = legs_for(points, pairs)
        for criterion in ("distance", "emission"):
            started = time.perf_counter()
            result = optimize_route(criterion, package["vehicle_mass_kg"], len(points), legs,
                                    load_ratio=package["load_ratio"], seed=trial["ga_seed"], ga_parameters=ga)
            route = [points[i] for i in result.sequence]
            stored = trial[f"route_{criterion}"]
            stored_kg = trial[f"e_{criterion}_kg"]
            match = route == stored and abs(result.total_emission_g / 1000 - stored_kg) < 1e-9
            same += match
            results.append({"trial": trial["trial"], "criterion": criterion, "route": route,
                            "emission_kg": result.total_emission_g / 1000, "same_as_2026_10_19": match})
            print(f"ensaio {trial['trial']:>2} {criterion:<8} {'igual' if match else 'DIFERENTE'} "
                  f"({time.perf_counter() - started:.1f} s)", flush=True)

    print(f"\n{same} de {len(results)} rotas iguais às de 2026-10-19")
    if args.output:
        args.output.write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0 if same == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
