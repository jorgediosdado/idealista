# Architecture and Operating Model

## System Architecture

```
scraper.py
│
├── Browser layer (Playwright + Chromium, headless=False)
│   ├── Search page tab      — navigates neighbourhood search result pages
│   └── Detail page tab      — single shared tab reused for every detail page visit
│
├── Scraping layer
│   ├── scrape_cards()       — extracts listing cards from a search results page
│   └── get_detail()         — extracts full detail fields from a listing page
│
├── State layer (listings.db via SQLite)
│   ├── init_db()            — creates schema on first use, migrates new columns
│   ├── load_seen_ids()      — loads all known listing URLs from the DB
│   └── upsert_listing()     — inserts new listings or updates price/last_seen
│
└── Config (config.json)
    └── neighbourhoods, max_price, min_sqm, min_rooms
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
    Stop early if a full page has no new listings
```

Paginates up to `MAX_PAGES` pages (configurable at the top of `scraper.py`) rather than just page 1. This handles the case where Idealista surfaces updated listings (price changes, re-listings) on page 1, which can push genuinely new listings to page 2 or 3.

Only visits detail pages for new listings — existing listings get price and `last_seen` updated from the card alone, keeping runs fast.

### Why not just page 1?

Idealista sorts by "most recently active", not strictly "most recently published". A listing that drops its price gets bumped back to page 1, potentially displacing a brand new listing. Checking up to 3 pages catches these edge cases without making runs too slow.

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
con-precio-hasta_{max_price},metros-cuadrados-mas-de_{min_sqm},habitaciones_{min_rooms}
```

Example: `con-precio-hasta_450000,metros-cuadrados-mas-de_90,habitaciones_2`

### Configured neighbourhoods

| Slug | Display name |
|---|---|
| `ciudad-vieja-centro` | Ciudad Vieja - Centro |
| `ensanche-juan-florez` | Ensanche - Juan Flórez |
| `riazor-visma` | Riazor - Visma |
| `monte-alto-zalaeta-atocha` | Monte Alto - Zalaeta - Atocha |
| `cuatro-caminos-plaza-de-la-cubela` | Cuatro Caminos - Plaza de la Cubela |
| `agra-del-orzan-ventorrillo` | Agra del Orzán - Ventorrillo |
