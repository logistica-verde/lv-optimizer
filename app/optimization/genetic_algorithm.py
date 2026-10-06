import time

import numpy as np

from app.models.chromosome import Chromosome
from app.optimization.crossover import order_crossover
from app.optimization.fitness.base import FitnessFunction
from app.optimization.mutation import inversion_mutation


class GeneticAlgorithm:
    def __init__(
        self,
        fitness_function: FitnessFunction,
        n_genes: int,
        population_size: int = 120,
        generations: int = 300,
        crossover_rate: float = 0.9,
        mutation_rate: float = 0.15,
        tournament_size: int = 3,
        elitism: int = 2,
        seed: int | None = None,
        time_limit_s: float | None = None,
    ):
        if elitism >= population_size:
            raise ValueError("elitism must be smaller than population_size")

        self.fitness_function = fitness_function
        self.n_genes = n_genes
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.elitism = elitism
        self.time_limit_s = time_limit_s
        self.rng = np.random.default_rng(seed)

    def initial_population(self) -> list[Chromosome]:
        return [Chromosome.random(self.n_genes, self.rng) for _ in range(self.population_size)]

    def evaluate(self, population: list[Chromosome]) -> None:
        for chromosome in population:
            chromosome.fitness = self.fitness_function.evaluate(chromosome)

    def select_parents(self, population: list[Chromosome], n_parents: int) -> list[Chromosome]:
        parents = []
        for _ in range(n_parents):
            contender_indices = self.rng.integers(0, len(population), size=self.tournament_size)
            contenders = [population[i] for i in contender_indices]
            parents.append(min(contenders, key=lambda c: c.fitness))
        return parents

    def next_generation(self, population: list[Chromosome]) -> list[Chromosome]:
        ranked = sorted(population, key=lambda c: c.fitness)
        offspring = [c.copy() for c in ranked[: self.elitism]]

        n_children = self.population_size - self.elitism
        parents = self.select_parents(ranked, n_children + n_children % 2)

        for i in range(0, len(parents), 2):
            parent1, parent2 = parents[i], parents[i + 1]
            if self.rng.random() < self.crossover_rate:
                child1, child2 = order_crossover(parent1, parent2, self.rng)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            offspring.append(inversion_mutation(child1, self.mutation_rate, self.rng))
            offspring.append(inversion_mutation(child2, self.mutation_rate, self.rng))

        offspring = offspring[: self.population_size]
        self.evaluate(offspring)
        return offspring

    def evolve(self) -> tuple[Chromosome, int]:
        start = time.perf_counter()
        population = self.initial_population()
        self.evaluate(population)

        generations_executed = 0
        for _ in range(self.generations):
            if self.time_limit_s is not None and time.perf_counter() - start > self.time_limit_s:
                break
            population = self.next_generation(population)
            generations_executed += 1

        best = min(population, key=lambda c: c.fitness)
        return best, generations_executed
