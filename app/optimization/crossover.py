import numpy as np

from app.models.chromosome import Chromosome


def order_crossover(
    parent1: Chromosome, parent2: Chromosome, rng: np.random.Generator
) -> tuple[Chromosome, Chromosome]:
    n = len(parent1)
    if n < 2:
        return parent1.copy(), parent2.copy()

    start, end = sorted(rng.choice(n, size=2, replace=False))
    child1 = Chromosome(_ox_child(parent1.genes, parent2.genes, start, end))
    child2 = Chromosome(_ox_child(parent2.genes, parent1.genes, start, end))
    return child1, child2


def _ox_child(donor: np.ndarray, filler: np.ndarray, start: int, end: int) -> np.ndarray:
    n = len(donor)
    child = np.full(n, -1, dtype=donor.dtype)
    child[start:end] = donor[start:end]

    inherited = set(child[start:end].tolist())
    remaining_genes = [g for g in np.concatenate([filler[end:], filler[:end]]) if g not in inherited]
    free_positions = np.concatenate([np.arange(end, n), np.arange(0, start)])

    child[free_positions] = remaining_genes
    return child
