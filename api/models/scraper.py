from typing import Optional
from pydantic import BaseModel


class LastRun(BaseModel):
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    new_listings: Optional[int] = None
    exit_code: Optional[int] = None


class ScraperStatus(BaseModel):
    running: bool
    last_run: Optional[LastRun] = None


class ScraperRunResponse(BaseModel):
    status: str
    started_at: str
