# idealista-scraper

Monitors Idealista property listings across selected A Coruña neighbourhoods. Detects new listings, tracks price changes, and exposes data via a REST API and Streamlit dashboard.

## Documentation

- [Architecture and Operating Model](docs/architecture-and-operating-model.md)
- [Data Model](docs/data-model.md)
- [FastAPI Plan](docs/fastapi-plan.md)

## Components

| File/Directory | Purpose |
|---|---|
| `scraper.py` | Playwright-based scraper — run manually or trigger via dashboard |
| `analyser.py` | CLI analysis tool — prints stats and exports `analysis.json` |
| `dashboard.py` | Streamlit dashboard — reads from API, includes scraper trigger |
| `api/` | FastAPI backend — listings, stats, config, scraper control |
| `config.json` | Search parameters (neighbourhoods, price, size, rooms) |
| `listings.db` | SQLite database — all listings ever seen |

## Running the system

**Step 1 — Start the API:**
```bash
python -m uvicorn api.main:app --reload
```
API runs on http://localhost:8000 · Docs at http://localhost:8000/docs

**Step 2 — Start the dashboard:**
```bash
python -m streamlit run dashboard.py --server.headless true
```
Dashboard runs on http://localhost:8501

The dashboard includes a **Run scraper** button in the sidebar — no need to open a terminal to scrape.

**Analyse (CLI):**
```bash
python analyser.py          # last 7 days
python analyser.py --days 30
python analyser.py --all
```

To reset and re-scrape from scratch: delete `listings.db`.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/listings` | All listings with filters (neighbourhood, price, elevator, etc.) |
| `GET` | `/listings/{url_id}` | Single listing by URL |
| `GET` | `/stats` | Aggregated stats (price range, avg €/m², by neighbourhood, etc.) |
| `GET` | `/price-history` | Price change log |
| `GET` | `/config` | Current search config |
| `PUT` | `/config` | Update search config |
| `POST` | `/scraper/run` | Trigger a scraper run |
| `GET` | `/scraper/status` | Check if scraper is running + last run info |
| `GET` | `/scraper/log` | Live log output from the current or last run |

## Search criteria

Configured in `config.json`:

```json
{
  "neighbourhoods": [...],
  "max_price": 550000,
  "min_sqm": 90,
  "min_rooms": 2
}
```

Can also be updated at runtime via `PUT /config`.

**Current neighbourhoods:**
- Ciudad Vieja - Centro
- Ensanche - Juan Flórez
- Riazor - Visma
- Monte Alto - Zalaeta - Atocha
- Cuatro Caminos - Plaza de la Cubela
- Agra del Orzán - Ventorrillo

To add a neighbourhood, find its slug in the Idealista URL:
```
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood-slug}/
```

## Scheduling

Run automatically twice a day via Windows Task Scheduler:

```powershell
schtasks /create /tn "IdealistaScraper" /tr "python C:\Users\Jorge\idealista-scraper\scraper.py" /sc daily /st 08:00 /du 0001:00 /ri 720 /f
```

Runs at 08:00, repeats every 720 minutes (12h). The machine must be on and not sleeping.

## Bot protection notes

Idealista uses DataDome. `requests`, `httpx`, and `curl_cffi` are all blocked. Playwright with `headless=False` works reliably. Key bypasses:
- `navigator.webdriver` set to `undefined`
- Real Chrome user agent + Spanish locale
- `--disable-blink-features=AutomationControlled`
- Random delays (3–8s per detail page, 4–10s between neighbourhoods)
- Single shared browser tab reused for all detail page visits

## Dependencies

```bash
pip install playwright pandas streamlit plotly fastapi "uvicorn[standard]" requests
playwright install chromium
```
