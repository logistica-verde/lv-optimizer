from __future__ import annotations

import numpy as np


class Chromosome:
    """Permutation-based individual: genes are indices over delivery points, depot excluded."""

    def __init__(self, genes: np.ndarray):
        self.genes = genes
        self.fitness: float | None = None

    @classmethod
    def random(cls, n_genes: int, rng: np.random.Generator) -> "Chromosome":
        return cls(rng.permutation(n_genes))

    def copy(self) -> "Chromosome":
        clone = Chromosome(self.genes.copy())
        clone.fitness = self.fitness
        return clone

    def decode_route(self, point_ids: list[str]) -> list[str]:
        return ["DEPOT"] + [point_ids[i] for i in self.genes] + ["DEPOT"]

    def __len__(self) -> int:
        return len(self.genes)
