import re
from typing import Optional
from api.database import get_connection
from api.models.stats import (
    StatsResponse, PriceStats, PpmStats, FeaturesStats,
    NeighbourhoodStat, PriceBucket, ConditionStat, EnergyRatingStat,
)


def _parse_price(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def _parse_ppm(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    d = re.sub(r"[^\d]", "", s.split("€")[0])
    return int(d) if d else None


def _avg(lst: list) -> Optional[float]:
    lst = [x for x in lst if x is not None]
    return sum(lst) / len(lst) if lst else None


def _median(lst: list) -> Optional[float]:
    lst = sorted(x for x in lst if x is not None)
    if not lst:
        return None
    mid = len(lst) // 2
    return float(lst[mid]) if len(lst) % 2 else (lst[mid - 1] + lst[mid]) / 2


PRICE_BUCKETS = [
    (0,       200_000, "< 200k"),
    (200_000, 250_000, "200k–250k"),
    (250_000, 300_000, "250k–300k"),
    (300_000, 350_000, "300k–350k"),
    (350_000, 400_000, "350k–400k"),
    (400_000, 500_000, "400k–450k"),
]


def get_stats(days: Optional[int] = None, neighbourhood: Optional[str] = None) -> StatsResponse:
    conditions = []
    params: list = []

    if days is not None:
        conditions.append("first_seen >= datetime('now', ?)")
        params.append(f"-{days} days")
    if neighbourhood:
        conditions.append("neighbourhood = ?")
        params.append(neighbourhood)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as conn:
        rows = conn.execute(f"SELECT * FROM listings {where}", params).fetchall()

    rows = [dict(r) for r in rows]
    prices = [_parse_price(r["price"]) for r in rows]
    ppms = [_parse_ppm(r["price_per_sqm"]) for r in rows]
    valid_p = [p for p in prices if p]
    valid_ppm = [p for p in ppms if p]

    # By neighbourhood
    by_n: dict[str, list] = {}
    for r in rows:
        by_n.setdefault(r["neighbourhood"], []).append(_parse_price(r["price"]))

    neighbourhood_stats = [
        NeighbourhoodStat(
            neighbourhood=n,
            count=len(ps),
            avg_price=_avg(ps),
            min_price=min((p for p in ps if p), default=None),
            max_price=max((p for p in ps if p), default=None),
        )
        for n, ps in sorted(by_n.items(), key=lambda x: -len(x[1]))
    ]

    # Price buckets
    from collections import Counter
    bucket_counts: Counter = Counter()
    for p in valid_p:
        for lo, hi, label in PRICE_BUCKETS:
            if lo <= p < hi:
                bucket_counts[label] += 1
                break
    price_distribution = [
        PriceBucket(bucket=label, count=bucket_counts.get(label, 0))
        for _, _, label in PRICE_BUCKETS
    ]

    # Condition breakdown
    cond_counts: Counter = Counter(r["condition"] for r in rows if r["condition"])
    condition_breakdown = [
        ConditionStat(condition=c, count=n) for c, n in cond_counts.most_common()
    ]

    # Energy ratings
    energy_counts: Counter = Counter(r["energy_rating"] for r in rows if r["energy_rating"])
    energy_ratings = [
        EnergyRatingStat(rating=r, count=n) for r, n in sorted(energy_counts.items())
    ]

    total = len(rows)
    with_elevator = sum(1 for r in rows if r["has_elevator"])
    with_terrace = sum(1 for r in rows if r["has_terrace"])
    baths = [r["bathrooms"] for r in rows if r["bathrooms"]]

    return StatsResponse(
        total=total,
        price=PriceStats(
            min=min(valid_p, default=None),
            max=max(valid_p, default=None),
            mean=_avg(valid_p),
            median=_median(valid_p),
        ),
        ppm=PpmStats(
            min=min(valid_ppm, default=None),
            max=max(valid_ppm, default=None),
            mean=_avg(valid_ppm),
        ),
        features=FeaturesStats(
            with_elevator=with_elevator,
            with_terrace=with_terrace,
            elevator_pct=int(100 * with_elevator / total) if total else 0,
            terrace_pct=int(100 * with_terrace / total) if total else 0,
            avg_bathrooms=_avg(baths),
        ),
        by_neighbourhood=neighbourhood_stats,
        price_distribution=price_distribution,
        condition_breakdown=condition_breakdown,
        energy_ratings=energy_ratings,
    )
