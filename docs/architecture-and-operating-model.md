# Architecture and Operating Model

## System Architecture

```
test_scraper.py
│
├── Browser layer (Playwright + Chromium)
│   ├── Search page tab      — navigates neighbourhood search result pages
│   └── Detail page tab      — shared tab reused for every detail page visit
│
├── Scraping layer
│   ├── scrape_cards()       — extracts listing cards from a search results page
│   └── get_detail()         — extracts publish date + description from a detail page
│
├── State layer (SQLite)
│   ├── init_db()            — creates listings.db and schema on first use
│   ├── load_seen_ids()      — loads all known listing URLs from the DB
│   └── upsert_listing()     — inserts new listings or updates price/last_seen
│
└── Output
    └── new_listings.json    — current run's new listings (convenience file)
```

### Why headless=False

Idealista uses **DataDome** bot protection. Headless Chromium is detected via missing browser APIs and graphics capabilities. Running with a visible window (`headless=False`) bypasses this reliably.

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

### First run (no `listings.db` or empty)

```
For each neighbourhood:
  Page 1, 2, 3, ... (sorted by newest first)
    For each listing card:
      Visit detail page → get publish date + description
      If published within last 30 days → add to new_listings.json
      Always → persist to listings.db
    If no listing on this page is recent → stop paginating this neighbourhood
```

This seeds the database with all known listings and gives the user a meaningful first result set (last 30 days only, not hundreds of stale listings).

### Subsequent runs

```
For each neighbourhood:
  Page 1 only (new listings always appear at the top, sorted by date)
    For each listing card:
      If URL not in listings.db → new listing
        Visit detail page → get publish date + description
        Add to new_listings.json
        Insert into listings.db
      If URL already in listings.db → update price + last_seen
```

Only visits detail pages for genuinely new listings, keeping each run fast (~5–10 seconds per neighbourhood on a quiet day).

### Scheduling

The script is designed to run twice a day via **Windows Task Scheduler** (08:00 and 20:00). See `README.md` for the setup commands.

### URL structure

```
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood}/{filters}/
https://www.idealista.com/venta-viviendas/a-coruna/{neighbourhood}/{filters}/pagina-{n}.htm
```

Sort parameter appended as query string: `?ordenado-por=fecha-publicacion-desc`

### Configured neighbourhoods

| Slug | Display name |
|---|---|
| `ciudad-vieja-centro` | Ciudad Vieja - Centro |
| `ensanche-juan-florez` | Ensanche - Juan Flórez |
| `riazor-visma` | Riazor - Visma |
| `monte-alto-zalaeta-atocha` | Monte Alto - Zalaeta - Atocha |
