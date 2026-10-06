import numpy as np
import pytest

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction
from app.optimization.fitness.distance import DistanceFitnessFunction


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
