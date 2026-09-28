import numpy as np

from app.models.chromosome import Chromosome


def test_random_chromosome_is_a_valid_permutation():
    rng = np.random.default_rng(42)

    chromosome = Chromosome.random(5, rng)

    assert sorted(chromosome.genes.tolist()) == list(range(5))


def test_decode_route_includes_depot_at_both_ends():
    chromosome = Chromosome(np.array([2, 0, 1]))

    route = chromosome.decode_route(["A", "B", "C"])

    assert route == ["DEPOT", "C", "A", "B", "DEPOT"]


def test_copy_returns_an_independent_genes_array():
    chromosome = Chromosome(np.array([0, 1, 2]))

    clone = chromosome.copy()
    clone.genes[0] = 99

    assert chromosome.genes[0] == 0
