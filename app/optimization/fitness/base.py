from abc import ABC, abstractmethod

from app.models.chromosome import Chromosome


class FitnessFunction(ABC):
    """Cost to minimize: lower fitness means a better route."""

    @abstractmethod
    def evaluate(self, chromosome: Chromosome) -> float:
        raise NotImplementedError
