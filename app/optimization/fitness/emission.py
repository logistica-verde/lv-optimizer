import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction, route_indices
from app.optimization.meet_emission_model import MeetEmissionModel


class SegmentEmissionFitnessFunction(FitnessFunction):
    """MEET emission E = f(v, m, i) with speed and slope given per leg, total route emission in grams.

    Vehicle mass is constant along the route, so every leg cost is precomputed once.
    """

    def __init__(
        self,
        distance_matrix_km: np.ndarray,
        speed_matrix_kmh: np.ndarray,
        slope_matrix_percent: np.ndarray,
        vehicle_mass_kg: float,
        return_to_depot: bool = True,
        load_ratio: float = 1.0,
    ):
        self.model = MeetEmissionModel(vehicle_mass_kg, load_ratio)
        self.return_to_depot = return_to_depot
        self.emission_matrix_g = self.model.calculate_emission(
            speed_matrix_kmh, slope_matrix_percent, distance_matrix_km
        )

    def leg_emissions_g(self, chromosome: Chromosome) -> np.ndarray:
        route = route_indices(chromosome.genes, self.return_to_depot)
        return self.emission_matrix_g[route[:-1], route[1:]]

    def evaluate(self, chromosome: Chromosome) -> float:
        return float(self.leg_emissions_g(chromosome).sum())
