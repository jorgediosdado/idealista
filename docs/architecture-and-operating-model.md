# Architecture and Operating Model

## System Architecture

```
scraper.py  ←── POST /scraper/run (subprocess, unbuffered stdout → scraper.log)
     │
     ▼
listings.db  (SQLite, WAL mode)
     │
     ▼
api/  (FastAPI + uvicorn, localhost:8000)
│
├── routers/         — HTTP layer (listings, stats, price_history, config, scraper)
├── services/        — business logic (queries, stats, subprocess management)
├── models/          — Pydantic schemas
└── database.py      — SQLite connection (WAL mode, row_factory)
     │
     ▼
dashboard.py  (Streamlit, localhost:8501)
     └── reads via requests to http://localhost:8000
```

### API layer structure

| Layer | Directory | Responsibility |
|---|---|---|
| Routers | `api/routers/` | HTTP endpoints — validate input, call services, return responses |
| Services | `api/services/` | Business logic — DB queries, stats, scraper subprocess control |
| Models | `api/models/` | Pydantic schemas for validation and serialisation |
| Database | `api/database.py` | SQLite connection factory (WAL mode, row_factory) |

### Why headless=False

Idealista uses **DataDome** bot protection. Headless Chromium is detected and blocked. Running with a visible window (`headless=False`) bypasses this reliably. The scraper must run on a local machine — cloud execution is not viable.

### Anti-detection measures

| Measure | Detail |
|---|---|
| Visible browser window | `headless=False` |
| Webdriver flag removed | `navigator.webdriver → undefined` |
| Plugin spoofing | `navigator.plugins → [1,2,3]` |
| Chrome runtime spoofed | `window.chrome = { runtime: {} }` |
| Real user agent | Chrome 124 on Windows 11 |
| Spanish locale | `locale="es-ES"` |
| Random delays | 3–8s between detail pages, 5–9s between search pages, 4–10s between neighbourhoods |
| Shared detail tab | Single tab reused for all detail visits |

---

## Operating Model

### First run (empty or missing `listings.db`)

```
For each neighbourhood:
  Page 1, 2, 3, ... (sorted newest first)
    For each listing card:
      If URL not in DB:
        Visit detail page → extract all fields
        Insert into listings.db
    Stop paginating when a full page has no new listings
```

Seeds the database with all currently available listings.

### Subsequent runs

```
For each neighbourhood:
  Page 1, 2, ... up to MAX_PAGES (default: 3)
    For each listing card:
      If URL not in DB → new listing
        Visit detail page → extract all fields
        Insert into listings.db
      If URL already in DB → update price + last_seen only
        If price changed → log old price to price_history
    Stop early if a full page has no new listings
```

Paginates up to `MAX_PAGES` pages. Idealista sorts by "most recently active" — a listing that drops its price gets bumped to page 1, potentially pushing a new listing to page 2 or 3. Checking up to 3 pages catches these cases.

### Scraper state

At the start of each run, `scraper.py` writes:
```json
{ "started_at": "2026-03-26T08:00:00", "finished_at": null, "new_listings": null, "exit_code": null }
```

At the end:
```json
{ "started_at": null, "finished_at": "2026-03-26T08:18:42", "new_listings": 3, "exit_code": 0 }
```

The API reads this file via `GET /scraper/status`. The dashboard polls this endpoint every 3 seconds while a run is in progress, showing a live log and a summary when done.

### Triggering a run

Two ways:
1. **Dashboard sidebar** — "Run scraper" button → `POST /scraper/run` → subprocess launched with unbuffered stdout (`-u`) piped to `scraper.log`
2. **Manually** — `python scraper.py` in a terminal

### Scheduling

Windows Task Scheduler runs `scraper.py` at 08:00 and 20:00. The machine must be on and logged in (not sleeping).

---

## URL structure

```
# Page 1
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood}/{filters}/?ordenado-por=fecha-publicacion-desc

# Page N
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood}/{filters}/pagina-{n}.htm?ordenado-por=fecha-publicacion-desc
```

### Filter format

```
con-precio-hasta_{max_price},metros-cuadrados-mas-de_{min_sqm},de-dos-dormitorios,de-tres-dormitorios,de-cuatro-cinco-habitaciones-o-mas
```

### Configured neighbourhoods

| Slug | Display name |
|---|---|
| `ciudad-vieja-centro` | Ciudad Vieja - Centro |
| `ensanche-juan-florez` | Ensanche - Juan Flórez |
| `riazor-visma` | Riazor - Visma |
| `monte-alto-zalaeta-atocha` | Monte Alto - Zalaeta - Atocha |
| `cuatro-caminos-plaza-de-la-cubela` | Cuatro Caminos - Plaza de la Cubela |
| `agra-del-orzan-ventorrillo` | Agra del Orzán - Ventorrillo |
