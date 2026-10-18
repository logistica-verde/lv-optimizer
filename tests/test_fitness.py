import numpy as np
import pytest

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction
from app.optimization.fitness.distance import DistanceFitnessFunction
from app.optimization.fitness.emission import (
    EmissionFitnessFunction,
    MeetCoefficients,
    SegmentEmissionFitnessFunction,
)
from app.optimization.meet_emission_model import MeetEmissionModel


@pytest.fixture
def distance_matrix():
    return np.array(
        [
            [0.0, 1.0, 2.0, 10.0],
            [1.0, 0.0, 4.0, 5.0],
            [2.0, 4.0, 0.0, 6.0],
            [10.0, 5.0, 6.0, 0.0],
        ]
    )


def test_fitness_function_base_cannot_be_instantiated():
    with pytest.raises(TypeError):
        FitnessFunction()


def test_distance_fitness_sums_route_segments_including_depot_legs(distance_matrix):
    fitness_function = DistanceFitnessFunction(distance_matrix)
    chromosome = Chromosome(np.array([0, 1, 2]))

    total = fitness_function.evaluate(chromosome)

    assert total == pytest.approx(1.0 + 4.0 + 6.0 + 10.0)


def test_distance_fitness_depends_on_visit_order(distance_matrix):
    fitness_function = DistanceFitnessFunction(distance_matrix)

    short_route = fitness_function.evaluate(Chromosome(np.array([0, 1, 2])))
    long_route = fitness_function.evaluate(Chromosome(np.array([0, 2, 1])))

    assert long_route == pytest.approx(1.0 + 5.0 + 6.0 + 2.0)
    assert short_route == pytest.approx(21.0)


def make_emission_fitness(distance_matrix, demands_kg, **overrides):
    params = dict(
        distance_matrix_km=distance_matrix,
        demands_kg=np.array(demands_kg, dtype=float),
        empty_mass_kg=1000.0,
        capacity_kg=1000.0,
        avg_speed_kmh=50.0,
    )
    params.update(overrides)
    return EmissionFitnessFunction(**params)


def test_emission_without_load_equals_base_emission_times_distance(distance_matrix):
    fitness_function = make_emission_fitness(distance_matrix, [0.0, 0.0, 0.0])
    chromosome = Chromosome(np.array([0, 1, 2]))

    emission = fitness_function.evaluate(chromosome)

    expected = fitness_function.base_emission_g_per_km() * (1.0 + 4.0 + 6.0 + 10.0)
    assert emission == pytest.approx(expected)


def test_emission_increases_with_load(distance_matrix):
    chromosome = Chromosome(np.array([0, 1, 2]))

    empty = make_emission_fitness(distance_matrix, [0.0, 0.0, 0.0]).evaluate(chromosome)
    loaded = make_emission_fitness(distance_matrix, [500.0, 500.0, 0.0]).evaluate(chromosome)

    assert loaded > empty


def test_emission_prefers_delivering_heavy_demand_first():
    uniform_matrix = np.full((4, 4), 10.0) - np.eye(4) * 10.0
    fitness_function = make_emission_fitness(uniform_matrix, [900.0, 0.0, 0.0])

    heavy_first = fitness_function.evaluate(Chromosome(np.array([0, 1, 2])))
    heavy_last = fitness_function.evaluate(Chromosome(np.array([1, 2, 0])))

    assert heavy_first < heavy_last


def test_emission_load_factor_follows_remaining_load_per_leg():
    distance_matrix = np.array(
        [
            [0.0, 10.0, 10.0],
            [10.0, 0.0, 10.0],
            [10.0, 10.0, 0.0],
        ]
    )
    coefficients = MeetCoefficients(load_beta=1.0)
    fitness_function = make_emission_fitness(
        distance_matrix, [500.0, 500.0], coefficients=coefficients
    )

    emission = fitness_function.evaluate(Chromosome(np.array([0, 1])))

    base = fitness_function.base_emission_g_per_km()
    expected = base * 10.0 * (2.0 + 1.5 + 1.0)
    assert emission == pytest.approx(expected)


def test_emission_base_depends_on_speed(distance_matrix):
    slow = make_emission_fitness(distance_matrix, [0.0, 0.0, 0.0], avg_speed_kmh=10.0)
    cruise = make_emission_fitness(distance_matrix, [0.0, 0.0, 0.0], avg_speed_kmh=50.0)

    assert slow.base_emission_g_per_km() > cruise.base_emission_g_per_km()



def make_segment_emission(distance_matrix, speed=50.0, slope=0.0, mass=7500.0, **overrides):
    shape = distance_matrix.shape
    params = dict(
        distance_matrix_km=distance_matrix,
        speed_matrix_kmh=np.full(shape, speed),
        slope_matrix_percent=np.full(shape, slope),
        vehicle_mass_kg=mass,
    )
    params.update(overrides)
    return SegmentEmissionFitnessFunction(**params)


def test_segment_emission_sums_meet_emission_over_every_leg(distance_matrix):
    fitness_function = make_segment_emission(distance_matrix)

    emission = fitness_function.evaluate(Chromosome(np.array([0, 1, 2])))

    per_km = float(MeetEmissionModel(7500.0).calculate_emission(50.0, 0.0, 1.0))
    assert emission == pytest.approx(per_km * (1.0 + 4.0 + 6.0 + 10.0))


def test_segment_emission_open_route_skips_the_return_leg(distance_matrix):
    fitness_function = make_segment_emission(distance_matrix, return_to_depot=False)

    emission = fitness_function.evaluate(Chromosome(np.array([0, 1, 2])))

    per_km = float(MeetEmissionModel(7500.0).calculate_emission(50.0, 0.0, 1.0))
    assert emission == pytest.approx(per_km * (1.0 + 4.0 + 6.0))


def test_segment_emission_uses_each_leg_speed_and_slope():
    distance_matrix = np.full((3, 3), 10.0) - np.eye(3) * 10.0
    speed = np.full((3, 3), 50.0)
    slope = np.zeros((3, 3))
    speed[0, 1] = 20.0
    slope[1, 2] = 3.0
    fitness_function = make_segment_emission(
        distance_matrix, speed_matrix_kmh=speed, slope_matrix_percent=slope, return_to_depot=False
    )

    legs = fitness_function.leg_emissions_g(Chromosome(np.array([0, 1])))

    model = MeetEmissionModel(7500.0)
    assert legs[0] == pytest.approx(float(model.calculate_emission(20.0, 0.0, 10.0)))
    assert legs[1] == pytest.approx(float(model.calculate_emission(50.0, 3.0, 10.0)))
