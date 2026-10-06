import numpy as np
import pytest

from app.models.chromosome import Chromosome
from app.optimization.crossover import order_crossover


@pytest.mark.parametrize("seed", range(50))
def test_children_are_always_valid_permutations(seed):
    rng = np.random.default_rng(seed)
    parent1 = Chromosome.random(10, rng)
    parent2 = Chromosome.random(10, rng)

    child1, child2 = order_crossover(parent1, parent2, rng)

    assert sorted(child1.genes.tolist()) == list(range(10))
    assert sorted(child2.genes.tolist()) == list(range(10))


def test_child_inherits_segment_from_donor_parent():
    class FixedRng:
        def choice(self, n, size, replace):
            return np.array([3, 1])

    parent1 = Chromosome(np.array([0, 1, 2, 3, 4, 5]))
    parent2 = Chromosome(np.array([5, 4, 3, 2, 1, 0]))

    child1, child2 = order_crossover(parent1, parent2, FixedRng())

    assert child1.genes[1:3].tolist() == [1, 2]
    assert child2.genes[1:3].tolist() == [4, 3]


def test_remaining_genes_follow_filler_parent_order():
    class FixedRng:
        def choice(self, n, size, replace):
            return np.array([1, 3])

    parent1 = Chromosome(np.array([0, 1, 2, 3, 4, 5]))
    parent2 = Chromosome(np.array([5, 4, 3, 2, 1, 0]))

    child1, _ = order_crossover(parent1, parent2, FixedRng())

    assert child1.genes.tolist() == [3, 1, 2, 0, 5, 4]


def test_single_gene_chromosomes_are_returned_unchanged():
    rng = np.random.default_rng(0)
    parent1 = Chromosome(np.array([0]))
    parent2 = Chromosome(np.array([0]))

    child1, child2 = order_crossover(parent1, parent2, rng)

    assert child1.genes.tolist() == [0]
    assert child2.genes.tolist() == [0]


def test_parents_are_not_modified():
    rng = np.random.default_rng(3)
    parent1 = Chromosome(np.array([0, 1, 2, 3, 4]))
    parent2 = Chromosome(np.array([4, 3, 2, 1, 0]))

    order_crossover(parent1, parent2, rng)

    assert parent1.genes.tolist() == [0, 1, 2, 3, 4]
    assert parent2.genes.tolist() == [4, 3, 2, 1, 0]
