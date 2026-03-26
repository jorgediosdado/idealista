# Plan: FastAPI Backend for Idealista Scraper

## Context
Jorge wants to restructure the system so that:
1. The Streamlit dashboard reads data from a FastAPI REST API instead of SQLite directly
2. Scraper runs can be triggered from the dashboard via the API
3. The scraper itself remains unchanged (Playwright headless=False is non-negotiable)

---

## Architecture

```
scraper.py  ←── POST /scraper/run (subprocess.Popen)
     │
     ▼
listings.db  ←── written by scraper only
     │
     ▼
api/  (FastAPI + uvicorn, localhost:8000)
     │
     ▼
dashboard.py  ←── reads via requests to http://localhost:8000
```

---

## Project Structure

```
idealista-scraper/
│
├── api/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, mounts all routers, CORS
│   ├── db.py                 # get_connection() — WAL mode, row_factory
│   ├── models.py             # Pydantic response models
│   └── routers/
│       ├── __init__.py
│       ├── listings.py       # GET /listings, GET /listings/{url_id}
│       ├── stats.py          # GET /stats
│       ├── price_history.py  # GET /price-history
│       ├── config.py         # GET /config, PUT /config
│       └── scraper.py        # POST /scraper/run, GET /scraper/status
│
├── scraper.py                # Add scraper_state.json writes only
├── analyser.py               # Unchanged
├── dashboard.py              # Replace sqlite reads with requests calls
├── config.json
├── listings.db
└── README.md
```

---

## API Endpoints

### Listings
```
GET /listings
  Query: neighbourhood, min_price, max_price, has_elevator, has_terrace,
         days, sort (price|first_seen|ppm), order (asc|desc), limit, offset
  Response: { "total": int, "listings": [Listing] }

GET /listings/{url_id}
  Response: Listing | 404
```

### Stats
```
GET /stats
  Query: days (int), neighbourhood (str)
  Response: { total, price: {min,max,mean,median}, ppm: {mean,min,max},
              features: {elevator_pct,...}, by_neighbourhood: [...],
              price_distribution: [...], condition_breakdown: [...] }
```

### Price History
```
GET /price-history
  Query: url (str, optional), days (int, optional)
  Response: [{ url, old_price, recorded_at, full_url }]
```

### Config
```
GET /config     → current config.json contents
PUT /config     → validates + atomically writes config.json
```

### Scraper
```
POST /scraper/run   → starts scraper subprocess, returns 409 if already running
GET /scraper/status → { running: bool, last_run: { started_at, finished_at, new_listings, exit_code } }
```

---

## Key Implementation Details

### api/db.py
- `get_connection()` returns a `sqlite3.Row`-factored connection
- Enable WAL mode on first connect: `PRAGMA journal_mode=WAL`
- `check_same_thread=False`

### api/routers/scraper.py
- Module-level `_process: subprocess.Popen | None` tracks running process
- `POST /scraper/run`: poll `_process.poll()` to check if running; launch via `subprocess.Popen(["python", "scraper.py"])`
- `GET /scraper/status`: read `scraper_state.json` for history; combine with live poll

### scraper.py changes (minimal)
- At start of `run()`: write `scraper_state.json` → `{started_at, finished_at: null, new_listings: null, exit_code: null}`
- At end of `run()`: update with `finished_at`, `new_listings` count, `exit_code: 0`

### api/main.py
- CORS: `allow_origins=["http://localhost:8501"]`
- Mount all routers with `/` prefix

### dashboard.py changes
- Replace `sqlite3.connect()` + `pd.read_sql_query()` calls with `requests.get("http://localhost:8000/listings")`
- Replace `load_price_history()` with `requests.get("http://localhost:8000/price-history")`
- Add sidebar section: scraper status + "Run scraper" button → `requests.post("http://localhost:8000/scraper/run")`
- Data transformations (price parsing, date parsing) stay the same — just different data source

### api/models.py — Pydantic models
- `Listing`: all DB fields + computed `price_num`, `ppm_num`, `full_url`
- `ListingsResponse`: `total: int`, `listings: List[Listing]`
- `StatsResponse`: nested price/feature/neighbourhood stats
- `ConfigModel`: neighbourhoods, max_price, min_sqm, min_rooms
- `ScraperStatus`: running, last_run

---

## Files Modified
- `scraper.py` — add `scraper_state.json` writes (~5 lines in `run()`)
- `dashboard.py` — replace DB reads with API calls, add scraper sidebar section
- `api/` — new directory (~400 lines across 7 files)

## Files Unchanged
- `analyser.py`
- `config.json`
- `listings.db`

---

## Dependencies to Add
```
fastapi
uvicorn[standard]
requests
```

---

## Running the System
```bash
# Terminal 1 — API
uvicorn api.main:app --reload

# Terminal 2 — Dashboard
python -m streamlit run dashboard.py --server.headless true
```

---

## Verification
1. `GET http://localhost:8000/listings` returns all listings as JSON
2. `GET http://localhost:8000/stats` matches analyser.py output
3. Dashboard loads with data from API (no sqlite3 imports remaining in dashboard.py)
4. `POST http://localhost:8000/scraper/run` opens a browser window and starts scraping
5. `GET http://localhost:8000/scraper/status` shows `running: true` while scraper is active
6. Dashboard sidebar "Run scraper" button triggers scrape end-to-end
