# Architecture and Operating Model

## System Architecture

```
scraper.py  ←──────────────────── POST /scraper/run (subprocess)
     │
     ▼
listings.db  (SQLite, WAL mode)
     │
     ▼
api/  (FastAPI + uvicorn, localhost:8000)
│
├── routers/         — HTTP layer (listings, stats, price_history, config, scraper)
├── services/        — business logic (queries, stats computation, scraper control)
├── models/          — Pydantic schemas (request/response validation)
└── database.py      — SQLite connection (WAL mode, row_factory)
     │
     ▼
dashboard.py  (Streamlit, localhost:8501)
     └── reads via requests to http://localhost:8000
```

### API structure

| Layer | Directory | Responsibility |
|---|---|---|
| Routers | `api/routers/` | HTTP endpoints — validate input, call services, return responses |
| Services | `api/services/` | Business logic — DB queries, stats computation, subprocess management |
| Models | `api/models/` | Pydantic schemas for request/response validation and serialisation |
| Database | `api/database.py` | SQLite connection factory with WAL mode and row_factory |

### Why headless=False

Idealista uses **DataDome** bot protection. Headless Chromium is detected via missing browser APIs and graphics capabilities. Running with a visible window (`headless=False`) bypasses this reliably. The scraper must run on a local machine — cloud execution is not viable.

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
| Shared detail tab | Single tab reused for all detail visits — avoids rapid tab open/close pattern |

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
    (Idealista loops back to page 1 when results are exhausted)
```

Seeds the database with all currently available listings across all pages.

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

Paginates up to `MAX_PAGES` pages (configurable at the top of `scraper.py`). Idealista sorts by "most recently active" — a listing that drops its price gets bumped to page 1, potentially pushing a new listing to page 2 or 3. Checking up to 3 pages catches these cases without making runs slow.

### Triggering a run

The scraper can be started in two ways:
1. **Manually:** `python scraper.py`
2. **Via API:** `POST /scraper/run` — launches `scraper.py` as a subprocess; returns 409 if already running

The scraper writes a `scraper_state.json` file at start and finish. The API reads this file to report last run time and new listing count via `GET /scraper/status`.

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
