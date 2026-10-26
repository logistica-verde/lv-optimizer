import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction, route_indices


class DistanceFitnessFunction(FitnessFunction):
    """Total route distance in km. Matrix index 0 is the depot; genes map to indices 1..n."""

    def __init__(
        self,
        distance_matrix_km: np.ndarray,
        return_to_depot: bool = True,
        end_index: int | None = None,
    ):
        self.distance_matrix_km = distance_matrix_km
        self.return_to_depot = return_to_depot
        self.end_index = end_index

    def evaluate(self, chromosome: Chromosome) -> float:
        route = route_indices(chromosome.genes, self.return_to_depot, self.end_index)
        return float(self.distance_matrix_km[route[:-1], route[1:]].sum())
