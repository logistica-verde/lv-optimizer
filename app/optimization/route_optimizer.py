from dataclasses import dataclass

import time

import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.fitness.base import route_indices
from app.optimization.fitness.distance import DistanceFitnessFunction
from app.optimization.fitness.emission import SegmentEmissionFitnessFunction
from app.optimization.genetic_algorithm import GeneticAlgorithm

TIME_LIMIT_S = 55.0


@dataclass(frozen=True)
class GaParameters:
    """Tuned on the synthetic instances: the default 120 x 300 with 15% mutation converged within
    ~15 generations on the emission criterion and missed the optimum on 10 points."""

    population_size: int = 300
    generations: int = 2000
    crossover_rate: float = 0.9
    mutation_rate: float = 0.4


DEFAULT_GA_PARAMETERS = GaParameters()


@dataclass(frozen=True)
class Leg:
    from_index: int
    to_index: int
    distance_km: float
    speed_kmh: float
    slope_percent: float


@dataclass(frozen=True)
class RouteResult:
    sequence: list[int]
    total_distance_km: float
    total_emission_g: float
    leg_emissions_g: list[tuple[int, int, float]]
    generations: int
    elapsed_s: float
    converged_at_generation: int
    best_fitness_history: list[float]


def build_matrices(point_count: int, legs: list[Leg]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    distance = np.zeros((point_count, point_count))
    speed = np.ones((point_count, point_count))
    slope = np.zeros((point_count, point_count))
    for leg in legs:
        distance[leg.from_index, leg.to_index] = leg.distance_km
        speed[leg.from_index, leg.to_index] = leg.speed_kmh
        slope[leg.from_index, leg.to_index] = leg.slope_percent
    return distance, speed, slope


def optimize_route(
    criterion: str,
    vehicle_mass_kg: float,
    point_count: int,
    legs: list[Leg],
    load_ratio: float = 1.0,
    seed: int | None = None,
    time_limit_s: float = TIME_LIMIT_S,
    ga_parameters: GaParameters | None = None,
) -> RouteResult:
    """Best visiting order over all points, starting at point 0 (depot) with no return leg.

    best_fitness_history is in the criterion's own unit: grams of CO2 or km.
    """
    ga_parameters = ga_parameters or DEFAULT_GA_PARAMETERS
    start = time.perf_counter()
    distance, speed, slope = build_matrices(point_count, legs)
    distance_fitness = DistanceFitnessFunction(distance, return_to_depot=False)
    emission_fitness = SegmentEmissionFitnessFunction(
        distance, speed, slope, vehicle_mass_kg, return_to_depot=False, load_ratio=load_ratio
    )
    fitness_function = emission_fitness if criterion == "emission" else distance_fitness

    n_genes = point_count - 1
    if n_genes < 2:
        best, generations = Chromosome(np.arange(n_genes)), 0
        history, converged_at = [fitness_function.evaluate(best)], 0
    else:
        ga = GeneticAlgorithm(
            fitness_function,
            n_genes,
            population_size=ga_parameters.population_size,
            generations=ga_parameters.generations,
            crossover_rate=ga_parameters.crossover_rate,
            mutation_rate=ga_parameters.mutation_rate,
            seed=seed,
            time_limit_s=time_limit_s,
        )
        best, generations = ga.evolve()
        history, converged_at = ga.best_fitness_history, ga.converged_at_generation()

    sequence = route_indices(best.genes, return_to_depot=False).tolist()
    leg_emissions = emission_fitness.leg_emissions_g(best)
    return RouteResult(
        sequence=sequence,
        total_distance_km=distance_fitness.evaluate(best),
        total_emission_g=float(leg_emissions.sum()),
        leg_emissions_g=[
            (sequence[i], sequence[i + 1], float(e)) for i, e in enumerate(leg_emissions)
        ],
        generations=generations,
        elapsed_s=time.perf_counter() - start,
        converged_at_generation=converged_at,
        best_fitness_history=history,
    )
