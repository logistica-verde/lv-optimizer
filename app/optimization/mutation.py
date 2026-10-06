import numpy as np

from app.models.chromosome import Chromosome


def inversion_mutation(
    chromosome: Chromosome, mutation_rate: float, rng: np.random.Generator
) -> Chromosome:
    n = len(chromosome)
    if n < 2 or rng.random() >= mutation_rate:
        return chromosome.copy()

    start, end = sorted(rng.choice(n, size=2, replace=False))
    genes = chromosome.genes.copy()
    genes[start : end + 1] = genes[start : end + 1][::-1]
    return Chromosome(genes)
