import asyncio
from concurrent.futures.process import BrokenProcessPool
from dataclasses import replace
from functools import partial
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app.optimization import process_pool, route_optimizer
from app.optimization.route_optimizer import GaParameters, Leg, optimize_route

router = APIRouter()


class SegmentIn(BaseModel):
    from_index: int = Field(ge=0)
    to_index: int = Field(ge=0)
    distance_meters: float = Field(ge=0)
    average_speed_kmh: float = Field(gt=0)
    slope_percent: float


class GaParamsIn(BaseModel):
    population_size: int | None = Field(default=None, ge=4, le=2000)
    generations: int | None = Field(default=None, ge=1, le=10000)
    crossover_rate: float | None = Field(default=None, ge=0, le=1)
    mutation_rate: float | None = Field(default=None, ge=0, le=1)


class OptimizeRequest(BaseModel):
    criterion: Literal["emission", "distance"]
    vehicle_mass_kg: float = Field(gt=0)
    point_count: int = Field(ge=1)
    segments: list[SegmentIn]
    load_ratio: float = Field(default=1.0, ge=0, le=1)
    seed: int | None = None
    end_index: int | None = Field(
        default=None,
        ge=1,
        description="Index of a point the route must finish at; the other points are visited in between",
    )
    return_to_depot: bool = Field(
        default=False,
        description="When true the route returns to point 0 after the last stop and the sequence ends with 0",
    )
    ga_params: GaParamsIn | None = Field(
        default=None,
        description="Genetic algorithm settings; the tuned defaults are used for omitted fields or when absent",
    )

    @model_validator(mode="after")
    def segments_cover_every_ordered_pair(self) -> "OptimizeRequest":
        n = self.point_count
        if self.end_index is not None:
            if self.end_index >= n:
                raise ValueError(f"end_index {self.end_index} is outside point_count {n}")
            if self.return_to_depot:
                raise ValueError("end_index and return_to_depot cannot be used together")
        pairs = set()
        for s in self.segments:
            if s.from_index >= n or s.to_index >= n:
                raise ValueError(f"segment {s.from_index}->{s.to_index} is outside point_count {n}")
            if s.from_index == s.to_index:
                raise ValueError(f"segment {s.from_index}->{s.to_index} links a point to itself")
            pair = (s.from_index, s.to_index)
            if pair in pairs:
                raise ValueError(f"segment {s.from_index}->{s.to_index} is duplicated")
            pairs.add(pair)
        expected = n * (n - 1)
        if len(pairs) != expected:
            raise ValueError(f"expected {expected} segments for {n} points, got {len(pairs)}")
        return self


class SegmentEmissionOut(BaseModel):
    from_index: int
    to_index: int
    emission_kg: float


class OptimizeResponse(BaseModel):
    sequence: list[int]
    total_emission_kg: float
    total_distance_meters: float
    segment_emissions: list[SegmentEmissionOut]
    generations: int
    elapsed_seconds: float
    converged_at_generation: int
    best_fitness_history: list[float] = Field(
        description="Best fitness after each generation (index 0 = initial population), "
        "in kg of CO2 for the emission criterion or meters for distance"
    )


def ga_parameters_of(request: OptimizeRequest) -> GaParameters:
    provided = request.ga_params.model_dump(exclude_none=True) if request.ga_params else {}
    return replace(route_optimizer.DEFAULT_GA_PARAMETERS, **provided)


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize(request: OptimizeRequest) -> OptimizeResponse:
    legs = [
        Leg(s.from_index, s.to_index, s.distance_meters / 1000, s.average_speed_kmh, s.slope_percent)
        for s in request.segments
    ]
    solve = partial(
        optimize_route, request.criterion, request.vehicle_mass_kg, request.point_count, legs,
        load_ratio=request.load_ratio, seed=request.seed, return_to_depot=request.return_to_depot,
        end_index=request.end_index,
        ga_parameters=ga_parameters_of(request),
    )
    try:
        result = await asyncio.get_running_loop().run_in_executor(process_pool.get_pool(), solve)
    except BrokenProcessPool:
        process_pool.reset_pool()
        raise
    return OptimizeResponse(
        sequence=result.sequence,
        total_emission_kg=result.total_emission_g / 1000,
        total_distance_meters=result.total_distance_km * 1000,
        segment_emissions=[
            SegmentEmissionOut(from_index=a, to_index=b, emission_kg=e / 1000)
            for a, b, e in result.leg_emissions_g
        ],
        generations=result.generations,
        elapsed_seconds=result.elapsed_s,
        converged_at_generation=result.converged_at_generation,
        best_fitness_history=[
            f / 1000 if request.criterion == "emission" else f * 1000 for f in result.best_fitness_history
        ],
    )
