from typing import Optional
from fastapi import APIRouter
from api.models.price_history import PriceHistoryEntry
from api.services import price_history_service

router = APIRouter(prefix="/price-history", tags=["price-history"])


@router.get("", response_model=list[PriceHistoryEntry])
def get_price_history(url: Optional[str] = None, days: Optional[int] = None):
    return price_history_service.get_price_history(url=url, days=days)
