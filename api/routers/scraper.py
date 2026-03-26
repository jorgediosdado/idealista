from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from api.models.scraper import ScraperStatus, ScraperRunResponse
from api.services import scraper_service

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/run", response_model=ScraperRunResponse)
def run_scraper():
    try:
        return scraper_service.run_scraper()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/status", response_model=ScraperStatus)
def get_status():
    return scraper_service.get_status()


@router.get("/log", response_class=PlainTextResponse)
def get_log(lines: int = 100):
    return scraper_service.get_log(last_n_lines=lines)
