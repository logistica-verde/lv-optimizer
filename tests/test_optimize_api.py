import itertools

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_request(point_count, criterion="distance", seed=7, speed=None, slope=None, **overrides):
    rng = np.random.default_rng(seed)
    coords = rng.random((point_count, 2)) * 5000
    segments = []
    for a, b in itertools.permutations(range(point_count), 2):
        segments.append(
            {
                "from_index": a,
                "to_index": b,
                "distance_meters": float(np.linalg.norm(coords[a] - coords[b])),
                "average_speed_kmh": speed(a, b) if speed else 40.0,
                "slope_percent": slope(a, b) if slope else 0.0,
            }
        )
    body = {
        "criterion": criterion,
        "vehicle_mass_kg": 3500.0,
        "point_count": point_count,
        "segments": segments,
        "seed": 42,
    }
    body.update(overrides)
    return body


def open_route_distance(body, sequence):
    lookup = {(s["from_index"], s["to_index"]): s["distance_meters"] for s in body["segments"]}
    return sum(lookup[(a, b)] for a, b in zip(sequence, sequence[1:]))


@pytest.mark.parametrize("criterion", ["distance", "emission"])
def test_optimize_returns_a_sequence_over_every_point_starting_at_depot(criterion):
    body = make_request(10, criterion=criterion)

    response = client.post("/optimize", json=body)

    assert response.status_code == 200
    data = response.json()
    assert data["sequence"][0] == 0
    assert sorted(data["sequence"]) == list(range(10))
    assert data["total_distance_meters"] == pytest.approx(open_route_distance(body, data["sequence"]))


def test_optimize_returns_one_emission_per_leg_matching_the_total():
    body = make_request(8, criterion="emission")

    data = client.post("/optimize", json=body).json()

    sequence = data["sequence"]
    legs = [(e["from_index"], e["to_index"]) for e in data["segment_emissions"]]
    assert legs == list(zip(sequence, sequence[1:]))
    assert data["total_emission_kg"] == pytest.approx(sum(e["emission_kg"] for e in data["segment_emissions"]))
    assert all(e["emission_kg"] > 0 for e in data["segment_emissions"])


def test_distance_criterion_finds_the_shortest_open_route_on_a_small_instance():
    body = make_request(7, criterion="distance")

    data = client.post("/optimize", json=body).json()

    best = min(
        open_route_distance(body, [0, *p]) for p in itertools.permutations(range(1, 7))
    )
    assert data["total_distance_meters"] == pytest.approx(best)


def test_emission_criterion_avoids_slow_uphill_legs_that_distance_ignores():
    def speed(a, b):
        return 8.0 if (a, b) == (0, 1) else 50.0

    def slope(a, b):
        return 8.0 if (a, b) == (0, 1) else 0.0

    coords_seed = 3
    distance_body = make_request(6, criterion="distance", seed=coords_seed, speed=speed, slope=slope)
    emission_body = make_request(6, criterion="emission", seed=coords_seed, speed=speed, slope=slope)

    distance_data = client.post("/optimize", json=distance_body).json()
    emission_data = client.post("/optimize", json=emission_body).json()

    assert emission_data["total_emission_kg"] <= distance_data["total_emission_kg"]
    assert emission_data["sequence"][:2] != [0, 1]


def test_same_seed_gives_same_sequence():
    body = make_request(12, criterion="emission")

    first = client.post("/optimize", json=body).json()
    second = client.post("/optimize", json=body).json()

    assert first["sequence"] == second["sequence"]


@pytest.mark.parametrize("point_count", [1, 2, 3])
def test_tiny_instances_are_answered(point_count):
    body = make_request(point_count)

    data = client.post("/optimize", json=body).json()

    assert sorted(data["sequence"]) == list(range(point_count))
    assert data["sequence"][0] == 0
    assert len(data["segment_emissions"]) == point_count - 1


def test_missing_segment_is_rejected():
    body = make_request(4)
    body["segments"] = body["segments"][1:]

    response = client.post("/optimize", json=body)

    assert response.status_code == 422


def test_segment_outside_point_count_is_rejected():
    body = make_request(3)
    body["segments"][0]["to_index"] = 9

    response = client.post("/optimize", json=body)

    assert response.status_code == 422


def test_unknown_criterion_is_rejected():
    response = client.post("/optimize", json=make_request(3, criterion="cost"))

    assert response.status_code == 422


def test_thirty_point_instance_stays_within_the_time_budget():
    body = make_request(30, criterion="emission")

    response = client.post("/optimize", json=body)

    assert response.status_code == 200
    assert sorted(response.json()["sequence"]) == list(range(30))


def test_load_ratio_outside_zero_to_one_is_rejected():
    response = client.post("/optimize", json=make_request(3, load_ratio=1.5))

    assert response.status_code == 422


def test_unloaded_vehicle_emits_less_on_the_same_route():
    loaded = client.post("/optimize", json=make_request(6, criterion="distance", load_ratio=1.0)).json()
    unloaded = client.post("/optimize", json=make_request(6, criterion="distance", load_ratio=0.0)).json()

    assert loaded["sequence"] == unloaded["sequence"]
    assert unloaded["total_emission_kg"] < loaded["total_emission_kg"]


@pytest.mark.parametrize("criterion, total_key", [("emission", "total_emission_kg"), ("distance", "total_distance_meters")])
def test_response_reports_convergence_in_the_criterion_unit(criterion, total_key):
    data = client.post("/optimize", json=make_request(10, criterion=criterion)).json()

    history = data["best_fitness_history"]
    assert len(history) == data["generations"] + 1
    assert history[-1] == pytest.approx(data[total_key])
    assert history[data["converged_at_generation"]] == pytest.approx(history[-1])
    assert 0 < data["elapsed_seconds"] < 60


@pytest.mark.parametrize("criterion", ["distance", "emission"])
def test_return_to_depot_closes_the_route_and_counts_the_return_leg(criterion):
    body = make_request(7, criterion, return_to_depot=True)

    data = client.post("/optimize", json=body).json()

    sequence = data["sequence"]
    assert sequence[0] == 0 and sequence[-1] == 0
    assert sorted(sequence[:-1]) == list(range(7))
    assert len(data["segment_emissions"]) == 7
    assert data["total_distance_meters"] == pytest.approx(open_route_distance(body, sequence))


def test_the_route_stays_open_by_default():
    data = client.post("/optimize", json=make_request(6)).json()

    assert data["sequence"][-1] != 0
    assert len(data["segment_emissions"]) == 5


def test_a_closed_route_is_never_shorter_than_the_open_one_for_the_same_points():
    open_route = client.post("/optimize", json=make_request(8, "distance")).json()
    closed_route = client.post("/optimize", json=make_request(8, "distance", return_to_depot=True)).json()

    assert closed_route["total_distance_meters"] >= open_route["total_distance_meters"] - 1e-6
