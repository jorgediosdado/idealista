from typing import Optional
from pydantic import BaseModel


class PriceStats(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    mean: Optional[float] = None
    median: Optional[float] = None


class PpmStats(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    mean: Optional[float] = None


class FeaturesStats(BaseModel):
    with_elevator: int
    with_terrace: int
    elevator_pct: int
    terrace_pct: int
    avg_bathrooms: Optional[float] = None


class NeighbourhoodStat(BaseModel):
    neighbourhood: str
    count: int
    avg_price: Optional[float] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None


class PriceBucket(BaseModel):
    bucket: str
    count: int


class ConditionStat(BaseModel):
    condition: str
    count: int


class EnergyRatingStat(BaseModel):
    rating: str
    count: int


class StatsResponse(BaseModel):
    total: int
    price: PriceStats
    ppm: PpmStats
    features: FeaturesStats
    by_neighbourhood: list[NeighbourhoodStat]
    price_distribution: list[PriceBucket]
    condition_breakdown: list[ConditionStat]
    energy_ratings: list[EnergyRatingStat]
