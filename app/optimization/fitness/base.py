from abc import ABC, abstractmethod

import numpy as np

from app.models.chromosome import Chromosome


class FitnessFunction(ABC):
    """Cost to minimize: lower fitness means a better route."""

    @abstractmethod
    def evaluate(self, chromosome: Chromosome) -> float:
        raise NotImplementedError


def route_indices(
    genes: np.ndarray, return_to_depot: bool = True, end_index: int | None = None
) -> np.ndarray:
    """Matrix indices visited by the route: depot 0, then genes shifted to 1..n.

    With end_index the route finishes at that fixed point: genes then cover the points other than
    the depot and the end, and the end index closes the route instead of the depot.
    """
    if end_index is not None:
        shifted = genes + 1
        shifted = shifted + (shifted >= end_index)
        return np.concatenate(([0], shifted, [end_index])).astype(int)
    tail = [0] if return_to_depot else []
    return np.concatenate(([0], genes + 1, tail)).astype(int)
