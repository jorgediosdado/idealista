import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional
from api.models.scraper import ScraperStatus, ScraperRunResponse, LastRun

STATE_FILE = "scraper_state.json"
LOG_FILE   = "scraper.log"

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
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(project_root, LOG_FILE)
    log_file = open(log_path, "w", encoding="utf-8", errors="replace")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    _process = subprocess.Popen(
        [sys.executable, "-u", "scraper.py"],
        cwd=project_root,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return ScraperRunResponse(status="started", started_at=started_at)


def get_log(last_n_lines: int = 100) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(project_root, LOG_FILE)
    if not os.path.exists(log_path):
        return ""
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-last_n_lines:])
