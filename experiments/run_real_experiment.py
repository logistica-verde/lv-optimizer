"""Validation experiment of the TCC on real roads: emission vs distance criterion.

Runs the complete system (OSRM street distances and speeds, SRTM slopes, MEET model, GA) through
the lv-api. Each trial picks a random subset of the registered delivery points and a start point
(the vehicle's current location), requests both criteria for the same trial and compares the
emission of the two routes:
    gain = (E_distance - E_emission) / E_distance * 100

Needs the stack running (deploy/docker-compose.yml) with at least --max-points delivery points.

    LV_API_URL=http://localhost LV_ADMIN_EMAIL=... LV_ADMIN_PASSWORD=... \
        python -m experiments.run_real_experiment --output-dir experiments/resultados-reais
"""

import argparse
import csv
import json
import math
import os
import random
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ORIGINS = {
    "Consolacao": (-23.5558, -46.6602),
    "Paulista-Trianon": (-23.5614, -46.6559),
    "Vila Mariana": (-23.5894, -46.6347),
    "Pinheiros": (-23.5668, -46.6923),
    "Mooca": (-23.5505, -46.5995),
    "Santana": (-23.5036, -46.6286),
}
SIZES = (5, 10, 14)
SUBSETS_PER_CELL = 3
T_CRITICAL_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
                 9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042, 60: 2.000}


def t_critical(degrees: int) -> float:
    keys = sorted(T_CRITICAL_95)
    return T_CRITICAL_95[max((k for k in keys if k <= degrees), default=keys[0])]


class Client:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.token = self.call("POST", "/api/auth/login", {"email": email, "senha": password})["token"]

    def call(self, method: str, path: str, body: dict | None = None) -> dict | list | None:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if getattr(self, "token", None):
            request.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read() or b"null")

    def route(self, vehicle_id: int, ids: list[int], origin: tuple[float, float], criterion: str) -> dict:
        accepted = self.call(
            "POST", "/api/routes/calculate",
            {"vehicleId": vehicle_id, "deliveryPointIds": ids, "criterion": criterion,
             "origin": {"latitude": origin[0], "longitude": origin[1]}},
        )
        while True:
            route = self.call("GET", f"/api/routes/{accepted['id']}")
            if route["status"] != "PENDING":
                return route
            time.sleep(0.5)


def order(route: dict) -> list[int]:
    return [p["pointId"] for p in sorted(route["points"], key=lambda p: p["visitOrder"])]


def run_trial(client: Client, vehicle_id: int, trial: dict) -> dict:
    started = time.time()
    with ThreadPoolExecutor(2) as pool:
        futures = {c: pool.submit(client.route, vehicle_id, trial["ids"], trial["origin"], c)
                   for c in ("DISTANCE", "EMISSION")}
        routes = {c: f.result() for c, f in futures.items()}
    row = {k: trial[k] for k in ("trial", "origin_name", "points")}
    row["seconds"] = round(time.time() - started, 1)
    if any(r["status"] != "COMPLETED" for r in routes.values()):
        row.update(status="FAILED", gain_percent=None)
        return row
    d, e = routes["DISTANCE"], routes["EMISSION"]
    row.update(
        status="COMPLETED",
        e_distance_kg=d["totalEmissionKg"], e_emission_kg=e["totalEmissionKg"],
        km_distance_route=d["totalDistanceMeters"] / 1000, km_emission_route=e["totalDistanceMeters"] / 1000,
        gain_percent=(d["totalEmissionKg"] - e["totalEmissionKg"]) / d["totalEmissionKg"] * 100,
        same_order=order(d) == order(e),
    )
    return row


def describe(values: list[float]) -> dict:
    n = len(values)
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if n > 1 else 0.0
    half = t_critical(n - 1) * std / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": mean, "std": std, "min": min(values), "max": max(values),
            "ci95_low": mean - half, "ci95_high": mean + half}


def summarize(rows: list[dict]) -> dict:
    done = [r for r in rows if r["status"] == "COMPLETED"]
    gains = [r["gain_percent"] for r in done]
    by_size = {
        str(size): describe([r["gain_percent"] for r in done if r["points"] == size])
        for size in sorted({r["points"] for r in done})
    }
    by_origin = {
        name: describe([r["gain_percent"] for r in done if r["origin_name"] == name])
        for name in dict.fromkeys(r["origin_name"] for r in done)
    }
    return {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trials": len(rows), "completed": len(done), "failed": len(rows) - len(done),
        "overall": describe(gains) if gains else None,
        "trials_with_gain": sum(g > 0.05 for g in gains),
        "trials_without_gain": sum(abs(g) <= 0.05 for g in gains),
        "trials_worse": sum(g < -0.05 for g in gains),
        "max_seconds": max((r["seconds"] for r in rows), default=0),
        "by_size": by_size, "by_origin": by_origin,
    }


def write_results(rows: list[dict], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (output_dir / "execucoes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "resumo.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def print_table(title: str, groups: dict) -> None:
    print(f"\n{title}")
    for name, g in groups.items():
        print(f"  {name:<18} n={g['n']:>2}  ganho medio {g['mean']:6.2f}%  desvio {g['std']:5.2f}  "
              f"IC95 [{g['ci95_low']:.2f}; {g['ci95_high']:.2f}]  min {g['min']:.2f}  max {g['max']:.2f}")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/resultados-reais"))
    parser.add_argument("--subsets", type=int, default=SUBSETS_PER_CELL)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)

    client = Client(os.environ.get("LV_API_URL", "http://localhost"),
                    os.environ["LV_ADMIN_EMAIL"], os.environ["LV_ADMIN_PASSWORD"])
    vehicle_id = next(v["id"] for v in client.call("GET", "/api/vehicles") if v["ativo"])
    all_ids = [p["id"] for p in client.call("GET", "/api/delivery-points") if p.get("ativo", True)]
    sizes = [s for s in SIZES if s <= len(all_ids)]
    rng = random.Random(args.seed)

    trials = []
    for origin_name, origin in ORIGINS.items():
        for size in sizes:
            for _ in range(args.subsets):
                trials.append({"trial": len(trials) + 1, "origin_name": origin_name, "origin": origin,
                               "points": size, "ids": rng.sample(all_ids, size)})

    rows = []
    for trial in trials:
        row = run_trial(client, vehicle_id, trial)
        rows.append(row)
        gain = "falhou" if row["gain_percent"] is None else f"{row['gain_percent']:+6.2f}%"
        print(f"[{row['trial']:>2}/{len(trials)}] {row['origin_name']:<16} {row['points']:>2} pts  "
              f"{gain}  {row['seconds']:.1f}s", flush=True)

    summary = summarize(rows)
    write_results(rows, summary, args.output_dir)
    print_table("Geral", {"todas": summary["overall"]})
    print_table("Por tamanho (pontos)", summary["by_size"])
    print_table("Por ponto de saida", summary["by_origin"])
    print(f"\n{summary['trials_with_gain']} com ganho, {summary['trials_without_gain']} iguais, "
          f"{summary['trials_worse']} piores, {summary['failed']} falhas, maior tempo {summary['max_seconds']}s")
    return summary


if __name__ == "__main__":
    main()
