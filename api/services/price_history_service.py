from typing import Optional
from api.database import get_connection
from api.models.price_history import PriceHistoryEntry


def get_price_history(
    url: Optional[str] = None,
    days: Optional[int] = None,
) -> list[PriceHistoryEntry]:
    conditions = []
    params: list = []

    if url:
        conditions.append("url = ?")
        params.append(url)
    if days is not None:
        conditions.append("recorded_at >= datetime('now', ?)")
        params.append(f"-{days} days")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM price_history {where} ORDER BY recorded_at DESC", params
        ).fetchall()

    return [PriceHistoryEntry(**dict(r)) for r in rows]
