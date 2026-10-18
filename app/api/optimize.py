from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app.optimization.route_optimizer import Leg, optimize_route

router = APIRouter()


class SegmentIn(BaseModel):
    from_index: int = Field(ge=0)
    to_index: int = Field(ge=0)
    distance_meters: float = Field(ge=0)
    average_speed_kmh: float = Field(gt=0)
    slope_percent: float


class OptimizeRequest(BaseModel):
    criterion: Literal["emission", "distance"]
    vehicle_mass_kg: float = Field(gt=0)
    point_count: int = Field(ge=1)
    segments: list[SegmentIn]
    load_ratio: float = Field(default=1.0, ge=0, le=1)
    seed: int | None = None

    @model_validator(mode="after")
    def segments_cover_every_ordered_pair(self) -> "OptimizeRequest":
        n = self.point_count
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


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    legs = [
        Leg(s.from_index, s.to_index, s.distance_meters / 1000, s.average_speed_kmh, s.slope_percent)
        for s in request.segments
    ]
    result = optimize_route(
        request.criterion, request.vehicle_mass_kg, request.point_count, legs,
        load_ratio=request.load_ratio, seed=request.seed,
    )
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
