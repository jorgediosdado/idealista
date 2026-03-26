# idealista-scraper

## Documentation

- [Architecture and Operating Model](docs/architecture-and-operating-model.md)
- [Data Model](docs/data-model.md)

Monitors Idealista property listings across selected A Coruña neighbourhoods and flags new ones matching configured criteria. Runs via Windows Task Scheduler twice a day.

## How it works

**First run** (no `seen_ids.json`):
1. Paginates all pages across every configured neighbourhood
2. Visits each listing's detail page to get publish date and full description
3. Includes only listings published in the last 30 days in `new_listings.json`
4. Saves all seen listing IDs to `seen_ids.json`

**Subsequent runs:**
1. Scrapes page 1 of each neighbourhood (new listings always appear at the top, sorted by date)
2. For listings not in `seen_ids.json`: visits detail page to get publish date and description
3. Writes only new listings to `new_listings.json`

## Usage

```bash
python test_scraper.py
```

To reset and re-run as if fresh: delete `listings.db`.

## Output files

| File | Description |
|---|---|
| `listings.db` | SQLite database — all listings ever seen, with full history |
| `new_listings.json` | New listings since last run — convenience output for the current run |

### Database schema

```
listings(url, neighbourhood, title, price, details, published, description, first_seen, last_seen)
```

- `url` — primary key (`/inmueble/123456/`)
- `first_seen` / `last_seen` — ISO datetimes; `last_seen` is updated on every run
- `price` — updated on every run (tracks price changes over time)

To reset and re-run as if fresh: delete `listings.db`.

## Current search criteria

- **Neighbourhoods:** Ciudad Vieja - Centro, Ensanche - Juan Flórez, Riazor - Visma, Monte Alto - Zalaeta - Atocha
- **Max price:** 450,000€
- **Min size:** 90 m²
- **Sorted by:** most recently published first

### Changing neighbourhoods

Edit the `NEIGHBOURHOODS` list in `test_scraper.py`. Use the neighbourhood slug from the Idealista URL:

```
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood-slug}/
```

### Changing price / size filters

Edit `FILTERS` in `test_scraper.py`:

```
con-precio-hasta_{max},metros-cuadrados-mas-de_{min}
```

## Scheduling (Windows Task Scheduler)

Run the following in an **elevated** command prompt to schedule twice-daily execution:

```cmd
schtasks /create /tn "IdealistaScraper-AM" /tr "python C:\Users\Jorge\idealista-scraper\test_scraper.py" /sc DAILY /st 08:00 /f
schtasks /create /tn "IdealistaScraper-PM" /tr "python C:\Users\Jorge\idealista-scraper\test_scraper.py" /sc DAILY /st 20:00 /f
```

## Bot protection notes

Idealista uses DataDome. The following do not work: `requests`, `httpx`, `curl_cffi`. Playwright with `headless=False` works reliably. Key bypasses applied:
- `navigator.webdriver` set to `undefined`
- Real Chrome user agent + Spanish locale
- `--disable-blink-features=AutomationControlled`
- Random delays between requests (3–8s per detail page, 4–10s between neighbourhoods)
- Single shared browser tab for detail page visits

## Dependencies

- Python 3.x
- `playwright` — `pip install playwright && playwright install chromium`
