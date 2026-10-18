from dataclasses import dataclass

import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import FitnessFunction, route_indices
from app.optimization.meet_emission_model import MeetEmissionModel


@dataclass(frozen=True)
class MeetCoefficients:
    """E_base(v) [g/km] = k0 + k1*v + k2*v^2 + k3/v; load factor = 1 + load_beta * load_ratio.

    Reference values, meant to be replaced by the vehicle-category coefficients from MEET/COPERT.
    """

    k0: float = 900.0
    k1: float = -8.5
    k2: float = 0.09
    k3: float = 4500.0
    load_beta: float = 0.35


def base_emission_g_per_km(speed_kmh: np.ndarray | float, coefficients: MeetCoefficients) -> np.ndarray:
    c = coefficients
    v = np.maximum(speed_kmh, 1e-3)
    return c.k0 + c.k1 * v + c.k2 * v**2 + c.k3 / v


class EmissionFitnessFunction(FitnessFunction):
    """MEET emission model E = f(v, m, i), flat terrain (i = 0), total route emission in grams.

    Vehicle mass is recomputed per leg as the remaining load shrinks with each delivery.
    """

    def __init__(
        self,
        distance_matrix_km: np.ndarray,
        demands_kg: np.ndarray,
        empty_mass_kg: float,
        capacity_kg: float,
        avg_speed_kmh: float,
        coefficients: MeetCoefficients | None = None,
    ):
        self.distance_matrix_km = distance_matrix_km
        self.demands_kg = demands_kg
        self.empty_mass_kg = empty_mass_kg
        self.capacity_kg = capacity_kg
        self.avg_speed_kmh = avg_speed_kmh
        self.coefficients = coefficients or MeetCoefficients()

    def base_emission_g_per_km(self) -> float:
        return float(base_emission_g_per_km(self.avg_speed_kmh, self.coefficients))

    def evaluate(self, chromosome: Chromosome) -> float:
        route = route_indices(chromosome.genes)
        leg_distances_km = self.distance_matrix_km[route[:-1], route[1:]]

        total_demand_kg = self.demands_kg.sum()
        delivered_kg = np.concatenate(([0.0], np.cumsum(self.demands_kg[chromosome.genes])))
        remaining_load_kg = np.clip(total_demand_kg - delivered_kg, 0.0, total_demand_kg)
        vehicle_mass_kg = self.empty_mass_kg + remaining_load_kg

        load_ratio = np.clip(
            (vehicle_mass_kg - self.empty_mass_kg) / self.capacity_kg, 0.0, 1.0
        )
        load_factor = 1.0 + self.coefficients.load_beta * load_ratio

        emission_g_per_km = self.base_emission_g_per_km() * load_factor
        return float((emission_g_per_km * leg_distances_km).sum())


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
