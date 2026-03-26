# Plan: Fotocasa Scraper Integration

## Context
The Idealista scraper is fully operational with FastAPI backend and Streamlit dashboard. The user now wants to add Fotocasa (fotocasa.es) as a second data source. A test script (`test_fotocasa.py`) confirmed Fotocasa has no bot detection — 31 `article` elements were found on the first page load, no captcha triggered. The goal is to scrape Fotocasa listings into the same `listings.db`, expose them through the existing API, and surface them in the dashboard alongside Idealista listings.

---

## Key Findings

- Fotocasa supports per-district slugs matching Idealista's (e.g. `riazor-visma` confirmed working)
- Per-district URL pattern: `https://www.fotocasa.es/es/comprar/viviendas/a-coruna-capital/{slug}/l`
- Fotocasa also exposes a combined multi-zone URL via `?combinedLocationIds=...` — not needed since we iterate per district
- Listing cards: `article` selector (31 found in test on the all-zones URL)
- No bot detection triggered — headless=False is kept for consistency but not required
- Child selectors inside `article` need to be discovered during implementation (see Phase 1 below)
- Pagination URL pattern needs to be discovered (likely `?page=2` appended to the district URL)
- Idealista's `url` column stores relative paths (e.g. `/venta-viviendas/...`); Fotocasa paths will be `/es/comprar/vivienda/...` — no collision risk on PRIMARY KEY
- `full_url` in `api/models/listing.py` hardcodes `https://www.idealista.com` — must become source-aware
- Price/size/rooms filter URL format for Fotocasa needs investigation (different from Idealista's filter string)

---

## Architecture

```
fotocasa_scraper.py  ←── POST /scraper/run?source=fotocasa
        │
        ▼
listings.db  (same DB, new `source` column)
        │
        ▼
api/  (existing FastAPI — add source filter to /listings)
        │
        ▼
dashboard.py  (add source multiselect + Fotocasa run button)
```

---

## DB Change

Add `source` column to `listings` table via migration in both scrapers' `init_db()`:

```sql
ALTER TABLE listings ADD COLUMN source TEXT DEFAULT 'idealista'
```

This is idempotent if wrapped in try/except (SQLite raises `OperationalError` if column already exists).

The `price_history` table does not need a `source` column — `url` is sufficient to join back.

---

## Files to Create

### `fotocasa_scraper.py`

Standalone scraper following the same structure as `scraper.py`:

```
Constants:
  BASE_URL = "https://www.fotocasa.es"
  STATE_FILE = "fotocasa_state.json"
  MAX_PAGES = 3  # same as Idealista default

Functions:
  init_db()                   — open listings.db, run source column migration
  write_state(data)           — write fotocasa_state.json (same pattern as scraper.py)
  district_url(slug, page)    — f"{BASE_URL}/es/comprar/viviendas/a-coruna-capital/{slug}/l"
                                  for page 1; append "?page={n}" for page 2+
  scrape_cards(page)          — extract url, title, price, details from article elements
  get_detail(page, url)       — extract bathrooms, energy_rating, has_elevator, etc.
  upsert_listing(data)        — INSERT OR REPLACE with source='fotocasa'; log price changes
  run()                       — iterate neighbourhoods from config.json, paginate, skip seen URLs
```

**Neighbourhood slugs**: Use the same slugs from `config.json` (Fotocasa slugs match Idealista slugs exactly — `riazor-visma` confirmed). Neighbourhood stored per listing same as Idealista.

**Phase 1 of implementation**: Before writing the full scraper, open a district URL in the browser and inspect `article` children to find exact CSS selectors for title, price, size, and href. Document as constants:

```python
SEL_TITLE  = "..."   # e.g. "[class*='re-CardTitle']"
SEL_PRICE  = "..."   # e.g. "[class*='re-CardPrice']"
SEL_DETAIL = "..."   # e.g. "[class*='re-CardFeatures']"
SEL_URL    = "a"     # first anchor inside article
```

**Filters**: Fotocasa price/size/rooms filters use a different URL format from Idealista. Investigate during implementation — may use query params or path segments. Start with unfiltered district URLs and add filters once the format is confirmed.

**Pausing**: Fotocasa has no bot detection — use shorter delays (1–3s between pages, 2–5s between detail pages).

**State file**: writes `fotocasa_state.json` (separate from `scraper_state.json`) so both scrapers can track status independently.

---

## Files to Modify

### `scraper.py`
- Add `source` column migration to `init_db()` (try/except around ALTER TABLE)
- All `upsert_listing()` calls already don't set `source` — migration default `'idealista'` handles existing rows

### `api/models/listing.py`
- Add `source: str = "idealista"` field
- Update `full_url` computed field:
  ```python
  _BASE_URLS = {
      "idealista": "https://www.idealista.com",
      "fotocasa":  "https://www.fotocasa.es",
  }

  @computed_field
  @property
  def full_url(self) -> str:
      return self._BASE_URLS.get(self.source, "https://www.idealista.com") + self.url
  ```

### `api/services/listing_service.py`
- Add `source: str | None = None` param to `get_listings()`
- Filter: `if source: rows = [r for r in rows if r["source"] == source]`

### `api/routers/listings.py`
- Add `source: str | None = Query(None)` parameter, pass to service

### `api/services/scraper_service.py`
- Add second state file constant: `FOTOCASA_STATE_FILE = "fotocasa_state.json"`
- Add second process tracker: `_fotocasa_process: Optional[subprocess.Popen] = None`
- `run_scraper(source="idealista")` — branch on source to pick script and process tracker
- `get_status(source="idealista")` — branch on source to pick state file and process

### `api/routers/scraper.py`
- `POST /scraper/run?source=idealista|fotocasa` — pass source to service
- `GET /scraper/status?source=idealista|fotocasa` — pass source to service
- `GET /scraper/log?source=idealista|fotocasa` — read `scraper.log` or `fotocasa.log`

### `dashboard.py`
- Add `source` multiselect filter in sidebar: `["Idealista", "Fotocasa"]` → maps to `["idealista", "fotocasa"]`
- Add Fotocasa run button below existing Idealista run button
- `load_data()` passes `source` param to `/listings` if filter is set

---

## API Changes Summary

| Endpoint | Change |
|---|---|
| `GET /listings` | Add `source` query param |
| `POST /scraper/run` | Add `source` query param (default: `idealista`) |
| `GET /scraper/status` | Add `source` query param |
| `GET /scraper/log` | Add `source` query param |

---

## Critical Files

| File | Role |
|---|---|
| `fotocasa_scraper.py` | New — full scraper for Fotocasa |
| `scraper.py` | Modify `init_db()` only (source column migration) |
| `api/models/listing.py` | Update `full_url` computed field, add `source` field |
| `api/services/scraper_service.py` | Support two scrapers |
| `api/routers/scraper.py` | Add `source` param to all endpoints |
| `api/services/listing_service.py` | Add `source` filter |
| `api/routers/listings.py` | Expose `source` param |
| `dashboard.py` | Add source filter + Fotocasa run button |

---

## Implementation Order

1. **Inspect Fotocasa HTML** — run `test_fotocasa.py` and inspect article innerHTML to discover selectors
2. **Write `fotocasa_scraper.py`** — using discovered selectors; test standalone with `python fotocasa_scraper.py`
3. **DB migration in `scraper.py`** — add source column ALTER TABLE to `init_db()`
4. **Update `api/models/listing.py`** — source field + source-aware full_url
5. **Update `api/services/listing_service.py` + `api/routers/listings.py`** — source filter
6. **Update `api/services/scraper_service.py` + `api/routers/scraper.py`** — dual scraper support
7. **Update `dashboard.py`** — source multiselect + Fotocasa run button

---

## Verification

1. Run `python fotocasa_scraper.py` — browser opens, listings appear in DB with `source='fotocasa'`
2. `GET /listings?source=fotocasa` returns only Fotocasa listings; `?source=idealista` returns only Idealista
3. `GET /listings` (no filter) returns both sources
4. `full_url` for a Fotocasa listing starts with `https://www.fotocasa.es`
5. `POST /scraper/run?source=fotocasa` triggers `fotocasa_scraper.py` subprocess
6. Dashboard source filter correctly narrows the listings table
7. Both scraper buttons work independently from the dashboard sidebar
