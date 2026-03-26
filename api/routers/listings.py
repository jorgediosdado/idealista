from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from api.models.listing import Listing, ListingsResponse
from api.services import listing_service

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=ListingsResponse)
def get_listings(
    neighbourhood: Optional[list[str]] = Query(default=None),
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    has_elevator: Optional[bool] = None,
    has_terrace: Optional[bool] = None,
    days: Optional[int] = None,
    sort: str = Query(default="first_seen", pattern="^(price|first_seen|ppm)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
    return listing_service.get_listings(
        neighbourhood=neighbourhood,
        min_price=min_price,
        max_price=max_price,
        has_elevator=has_elevator,
        has_terrace=has_terrace,
        days=days,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/{url_id:path}", response_model=Listing)
def get_listing(url_id: str):
    listing = listing_service.get_listing_by_url(f"/{url_id}")
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
