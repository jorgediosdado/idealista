import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional
from api.models.scraper import ScraperStatus, ScraperRunResponse, LastRun

STATE_FILE = "scraper_state.json"

_process: Optional[subprocess.Popen] = None


def _is_running() -> bool:
    global _process
    if _process is None:
        return False
    return _process.poll() is None


def _read_state() -> Optional[LastRun]:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return LastRun(**data)
    except Exception:
        return None


def get_status() -> ScraperStatus:
    return ScraperStatus(running=_is_running(), last_run=_read_state())


def run_scraper() -> ScraperRunResponse:
    global _process
    if _is_running():
        raise RuntimeError("Scraper is already running")

    started_at = datetime.now().isoformat()
    _process = subprocess.Popen(
        [sys.executable, "scraper.py"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return ScraperRunResponse(status="started", started_at=started_at)
