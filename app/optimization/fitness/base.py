from abc import ABC, abstractmethod

import numpy as np

from app.models.chromosome import Chromosome


class FitnessFunction(ABC):
    """Cost to minimize: lower fitness means a better route."""

    @abstractmethod
    def evaluate(self, chromosome: Chromosome) -> float:
        raise NotImplementedError


def route_indices(genes: np.ndarray, return_to_depot: bool = True) -> np.ndarray:
    """Matrix indices visited by the route: depot 0, then genes shifted to 1..n."""
    tail = [0] if return_to_depot else []
    return np.concatenate(([0], genes + 1, tail)).astype(int)
