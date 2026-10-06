import numpy as np
import pytest

from app.models.chromosome import Chromosome
from app.optimization.mutation import inversion_mutation


@pytest.mark.parametrize("seed", range(50))
def test_mutation_preserves_permutation(seed):
    rng = np.random.default_rng(seed)
    chromosome = Chromosome.random(10, rng)

    mutated = inversion_mutation(chromosome, mutation_rate=1.0, rng=rng)

    assert sorted(mutated.genes.tolist()) == list(range(10))


def test_mutation_rate_zero_keeps_genes():
    rng = np.random.default_rng(1)
    chromosome = Chromosome(np.array([0, 1, 2, 3, 4]))

    mutated = inversion_mutation(chromosome, mutation_rate=0.0, rng=rng)

    assert mutated.genes.tolist() == [0, 1, 2, 3, 4]


def test_mutation_reverses_the_selected_subsequence():
    class FixedRng:
        def random(self):
            return 0.0

        def choice(self, n, size, replace):
            return np.array([3, 1])

    chromosome = Chromosome(np.array([0, 1, 2, 3, 4, 5]))

    mutated = inversion_mutation(chromosome, mutation_rate=1.0, rng=FixedRng())

    assert mutated.genes.tolist() == [0, 3, 2, 1, 4, 5]


def test_mutation_does_not_modify_the_original_chromosome():
    rng = np.random.default_rng(2)
    chromosome = Chromosome(np.array([0, 1, 2, 3, 4]))

    inversion_mutation(chromosome, mutation_rate=1.0, rng=rng)

    assert chromosome.genes.tolist() == [0, 1, 2, 3, 4]


def test_single_gene_chromosome_is_returned_unchanged():
    rng = np.random.default_rng(0)
    chromosome = Chromosome(np.array([0]))

    mutated = inversion_mutation(chromosome, mutation_rate=1.0, rng=rng)

    assert mutated.genes.tolist() == [0]
