from typing import Optional
from fastapi import APIRouter
from api.models.stats import StatsResponse
from api.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(days: Optional[int] = None, neighbourhood: Optional[str] = None):
    return stats_service.get_stats(days=days, neighbourhood=neighbourhood)
