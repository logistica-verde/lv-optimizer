import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_optimize_api import make_request

client = TestClient(app)


def optimize(**ga_params):
    body = make_request(10, criterion="emission", ga_params=ga_params)
    return client.post("/optimize", json=body)


def test_the_generations_of_the_request_limit_the_run():
    response = optimize(generations=5)

    assert response.status_code == 200
    data = response.json()
    assert data["generations"] == 5
    assert len(data["best_fitness_history"]) == 6


def test_every_setting_of_the_request_is_accepted_together():
    response = optimize(population_size=30, generations=10, crossover_rate=0.7, mutation_rate=0.1)

    assert response.status_code == 200
    assert response.json()["generations"] == 10


def test_omitted_settings_keep_the_defaults():
    with_params = client.post("/optimize", json=make_request(8, ga_params={"generations": 7})).json()
    without = client.post("/optimize", json=make_request(8)).json()

    assert with_params["generations"] == 7
    assert without["generations"] == 300


def test_a_request_without_settings_uses_the_defaults():
    response = client.post("/optimize", json=make_request(8))

    assert response.status_code == 200
    assert response.json()["generations"] == 300


def test_the_same_seed_and_settings_give_the_same_route():
    first = optimize(population_size=40, generations=30).json()
    second = optimize(population_size=40, generations=30).json()

    assert first["sequence"] == second["sequence"]
    assert first["total_emission_kg"] == second["total_emission_kg"]


@pytest.mark.parametrize(
    "field, value",
    [
        ("population_size", 3),
        ("population_size", 5000),
        ("generations", 0),
        ("crossover_rate", 1.5),
        ("crossover_rate", -0.1),
        ("mutation_rate", 2),
    ],
)
def test_settings_outside_their_range_are_refused(field, value):
    response = optimize(**{field: value})

    assert response.status_code == 422
