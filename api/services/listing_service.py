import re
from typing import Optional
from api.database import get_connection
from api.models.listing import Listing, ListingsResponse

VALID_SORT = {"price": "price_num", "first_seen": "first_seen", "ppm": "ppm_num"}


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


def get_listings(
    neighbourhood: Optional[list[str]] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    has_elevator: Optional[bool] = None,
    has_terrace: Optional[bool] = None,
    days: Optional[int] = None,
    sort: str = "first_seen",
    order: str = "desc",
    limit: int = 100,
    offset: int = 0,
) -> ListingsResponse:
    conditions = []
    params: list = []

    if neighbourhood:
        placeholders = ",".join("?" * len(neighbourhood))
        conditions.append(f"neighbourhood IN ({placeholders})")
        params.extend(neighbourhood)

    if has_elevator is not None:
        conditions.append("has_elevator = ?")
        params.append(1 if has_elevator else 0)

    if has_terrace is not None:
        conditions.append("has_terrace = ?")
        params.append(1 if has_terrace else 0)

    if days is not None:
        conditions.append("first_seen >= datetime('now', ?)")
        params.append(f"-{days} days")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order_dir = "ASC" if order == "asc" else "DESC"

    with get_connection() as conn:
        all_rows = conn.execute(
            f"SELECT * FROM listings {where}", params
        ).fetchall()

    # Parse prices in Python for filtering and sorting
    rows = []
    for row in all_rows:
        d = dict(row)
        d["price_num"] = _parse_price(d.get("price"))
        d["ppm_num"] = _parse_ppm(d.get("price_per_sqm"))
        rows.append(d)

    if min_price is not None:
        rows = [r for r in rows if r["price_num"] and r["price_num"] >= min_price]
    if max_price is not None:
        rows = [r for r in rows if r["price_num"] and r["price_num"] <= max_price]

    sort_key = sort if sort in ("price_num", "ppm_num") else sort
    if sort == "price":
        sort_key = "price_num"
    elif sort == "ppm":
        sort_key = "ppm_num"
    else:
        sort_key = "first_seen"

    rows.sort(key=lambda r: (r.get(sort_key) is None, r.get(sort_key)), reverse=(order_dir == "DESC"))

    total = len(rows)
    page = rows[offset: offset + limit]

    listings = [Listing(**{k: v for k, v in r.items() if k not in ("price_num", "ppm_num")}) for r in page]
    return ListingsResponse(total=total, listings=listings)


def get_listing_by_url(url: str) -> Optional[Listing]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM listings WHERE url = ?", (url,)).fetchone()
    if not row:
        return None
    return Listing(**dict(row))
