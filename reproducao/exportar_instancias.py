"""Exporta as cinco instâncias sintéticas do experimento para reproducao/instancias/.

Cada arquivo traz os pontos (o ponto 0 é o depósito), como foram gerados e os trechos no formato
do POST /optimize, que também é o formato de --instances-dir do experimento.

    python -m reproducao.exportar_instancias
"""

import itertools
import json
from pathlib import Path

from experiments import run_experiment as experiment

OUTPUT = Path(__file__).resolve().parent / "instancias"


def export(point_count: int) -> dict:
    seed = point_count
    points = experiment.synthetic_points(point_count, seed)
    instance = experiment.synthetic_instance(point_count, seed)
    return {
        "name": instance.name,
        "point_count": point_count,
        "vehicle_mass_kg": instance.vehicle_mass_kg,
        "load_ratio": instance.load_ratio,
        "generation": {
            "function": "experiments.run_experiment.synthetic_instance",
            "seed": seed,
            "random_generator": "numpy.random.default_rng(seed)",
            "draw_order": "latitude, longitude, elevação (um valor por ponto) e velocidade (matriz n x n, simetrizada)",
            "latitude_range": experiment.LAT_RANGE,
            "longitude_range": experiment.LON_RANGE,
            "elevation_range_m": experiment.ELEVATION_RANGE_M,
            "speed_range_kmh": experiment.SPEED_RANGE_KMH,
            "max_slope_percent": experiment.MAX_SLOPE_PERCENT,
            "distance": "haversine entre os pontos (linha reta), sem rede viária",
            "slope": "(elevação destino - elevação origem) / distância, limitada a ±8%",
        },
        "points": [
            {
                "index": index,
                "depot": index == 0,
                "latitude": float(points.latitude[index]),
                "longitude": float(points.longitude[index]),
                "elevation_m": float(points.elevation_m[index]),
            }
            for index in range(point_count)
        ],
        "segments": [
            {
                "from_index": leg.from_index,
                "to_index": leg.to_index,
                "distance_meters": leg.distance_km * 1000,
                "average_speed_kmh": leg.speed_kmh,
                "slope_percent": leg.slope_percent,
            }
            for leg in instance.legs
        ],
        "speed_matrix_kmh": [[float(points.speed_kmh[a, b]) for b in range(point_count)] for a in range(point_count)],
        "pairs": point_count * (point_count - 1),
    }


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    for point_count in experiment.INSTANCE_SIZES:
        data = export(point_count)
        assert len(data["segments"]) == data["pairs"] == len(list(itertools.permutations(range(point_count), 2)))
        path = OUTPUT / f"{data['name']}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{path.name}: {point_count} pontos, {data['pairs']} trechos")


if __name__ == "__main__":
    main()
