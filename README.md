# idealista-scraper

Monitors Idealista property listings across selected A Coruña neighbourhoods. Detects new listings, tracks price changes, and exposes data via a Streamlit dashboard.

## Documentation

- [Architecture and Operating Model](docs/architecture-and-operating-model.md)
- [Data Model](docs/data-model.md)

## Components

| File | Purpose |
|---|---|
| `scraper.py` | Playwright-based scraper — run manually to collect listings |
| `analyser.py` | CLI analysis tool — prints stats and exports `analysis.json` |
| `dashboard.py` | Streamlit dashboard — interactive browser UI |
| `config.json` | Search parameters (neighbourhoods, price, size, rooms) |
| `listings.db` | SQLite database — all listings ever seen |

## Usage

**Scrape:**
```bash
python scraper.py
```

**Analyse:**
```bash
python analyser.py          # last 7 days
python analyser.py --days 30
python analyser.py --all
```

**Dashboard:**
```bash
python -m streamlit run dashboard.py --server.headless true
```
Then open http://localhost:8501

To reset and re-scrape from scratch: delete `listings.db`.

## Search criteria

Configured in `config.json`:

```json
{
  "neighbourhoods": [...],
  "max_price": 450000,
  "min_sqm": 90,
  "min_rooms": 2
}
```

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

## Bot protection notes

Idealista uses DataDome. `requests`, `httpx`, and `curl_cffi` are all blocked. Playwright with `headless=False` works reliably. Key bypasses applied:
- `navigator.webdriver` set to `undefined`
- Real Chrome user agent + Spanish locale
- `--disable-blink-features=AutomationControlled`
- Random delays (3–8s per detail page, 4–10s between neighbourhoods)
- Single shared browser tab reused for all detail page visits

## Dependencies

```bash
pip install playwright pandas streamlit plotly
playwright install chromium
```
