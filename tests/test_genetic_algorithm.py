import itertools

import numpy as np
import pytest

from app.models.chromosome import Chromosome
from app.optimization.fitness.distance import DistanceFitnessFunction
from app.optimization.genetic_algorithm import GeneticAlgorithm


def random_distance_matrix(n_points, seed):
    rng = np.random.default_rng(seed)
    coords = rng.random((n_points + 1, 2)) * 100
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def brute_force_best(fitness_function, n_genes):
    return min(
        fitness_function.evaluate(Chromosome(np.array(p)))
        for p in itertools.permutations(range(n_genes))
    )


def make_ga(fitness_function, n_genes, **overrides):
    params = dict(
        fitness_function=fitness_function,
        n_genes=n_genes,
        population_size=40,
        generations=60,
        seed=42,
    )
    params.update(overrides)
    return GeneticAlgorithm(**params)


@pytest.fixture
def fitness_function():
    return DistanceFitnessFunction(random_distance_matrix(7, seed=5))


def test_evolve_returns_valid_permutation_with_evaluated_fitness(fitness_function):
    best, generations = make_ga(fitness_function, 7).evolve()

    assert sorted(best.genes.tolist()) == list(range(7))
    assert best.fitness == pytest.approx(fitness_function.evaluate(best))
    assert generations == 60


def test_evolve_finds_the_optimum_on_a_small_instance(fitness_function):
    ga = make_ga(fitness_function, 7, population_size=80, generations=150)

    best, _ = ga.evolve()

    assert best.fitness == pytest.approx(brute_force_best(fitness_function, 7))


def test_evolve_beats_the_initial_population(fitness_function):
    ga = make_ga(fitness_function, 7)
    population = ga.initial_population()
    ga.evaluate(population)
    initial_best = min(c.fitness for c in population)

    best, _ = make_ga(fitness_function, 7).evolve()

    assert best.fitness <= initial_best


def test_same_seed_gives_same_result(fitness_function):
    first, _ = make_ga(fitness_function, 7).evolve()
    second, _ = make_ga(fitness_function, 7).evolve()

    assert first.genes.tolist() == second.genes.tolist()


def test_elitism_never_loses_the_best_individual(fitness_function):
    ga = make_ga(fitness_function, 7, elitism=2)
    population = ga.initial_population()
    ga.evaluate(population)

    for _ in range(20):
        best_before = min(c.fitness for c in population)
        population = ga.next_generation(population)
        assert min(c.fitness for c in population) <= best_before


def test_population_size_is_constant_across_generations(fitness_function):
    ga = make_ga(fitness_function, 7, population_size=31)
    population = ga.initial_population()
    ga.evaluate(population)

    next_population = ga.next_generation(population)

    assert len(next_population) == 31


def test_select_parents_returns_requested_number_and_favours_fitter(fitness_function):
    ga = make_ga(fitness_function, 7, tournament_size=5)
    population = ga.initial_population()
    ga.evaluate(population)

    parents = ga.select_parents(population, 200)

    assert len(parents) == 200
    assert np.mean([p.fitness for p in parents]) < np.mean([c.fitness for c in population])


def test_time_limit_stops_evolution_early(fitness_function):
    ga = make_ga(fitness_function, 7, generations=1_000_000, time_limit_s=0.05)

    _, generations = ga.evolve()

    assert 0 < generations < 1_000_000


def test_elitism_must_be_smaller_than_population(fitness_function):
    with pytest.raises(ValueError):
        make_ga(fitness_function, 7, population_size=10, elitism=10)
