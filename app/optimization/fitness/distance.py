import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction


class DistanceFitnessFunction(FitnessFunction):
    """Total route distance in km. Matrix index 0 is the depot; genes map to indices 1..n."""

    def __init__(self, distance_matrix_km: np.ndarray):
        self.distance_matrix_km = distance_matrix_km

    def evaluate(self, chromosome: Chromosome) -> float:
        route = np.concatenate(([0], chromosome.genes + 1, [0]))
        return float(self.distance_matrix_km[route[:-1], route[1:]].sum())
