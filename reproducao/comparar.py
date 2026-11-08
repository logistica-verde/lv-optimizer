"""Compara as colunas do AG de duas rodadas do experimento (execucoes.csv).

    python reproducao/comparar.py experiments/resultados-padrao-2026-11-07/execucoes.csv nova/execucoes.csv

Colunas comparadas: emissão e distância dos dois critérios, Δ, gerações e geração de convergência.
O tempo não entra: depende da máquina. A saída diz quantas execuções são idênticas e, nas
diferentes, em qual casa decimal começa a diferença.
"""

import csv
import sys

GA_COLUMNS = (
    "e_distance_kg", "e_emission_kg", "delta_percent", "km_distance_route", "km_emission_route",
    "generations_emission", "converged_at_emission",
)


def load(path: str) -> dict[tuple[str, str], dict]:
    with open(path, encoding="utf-8") as file:
        return {(row["instance"], row["seed"]): row for row in csv.DictReader(file)}


def first_differing_place(a: str, b: str) -> int | None:
    x, y = float(a), float(b)
    for places in range(0, 16):
        if round(x, places) != round(y, places):
            return places
    return None


def main(old_path: str, new_path: str) -> int:
    old, new = load(old_path), load(new_path)
    identical = 0
    for key in sorted(old):
        if key not in new:
            print(f"{key}: ausente na rodada nova")
            continue
        diffs = [(c, old[key][c], new[key][c]) for c in GA_COLUMNS if old[key][c] != new[key][c]]
        if not diffs:
            identical += 1
            continue
        for column, a, b in diffs:
            print(f"{key[0]} semente {key[1]}: {column} {a} -> {b} (difere a partir da casa {first_differing_place(a, b)})")
    print(f"Idênticas em todas as colunas do AG: {identical} de {len(old)}")
    return 0 if identical == len(old) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
