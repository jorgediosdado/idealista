# Data Model

## Database

**File:** `listings.db` (SQLite, WAL mode)

---

## Table: `listings`

Single table. Each row is a unique property listing identified by its Idealista URL.

| Column | Type | Description |
|---|---|---|
| `url` | TEXT PK | Relative URL path, e.g. `/inmueble/110223106/`. Stable unique identifier — used to detect new vs known listings. |
| `neighbourhood` | TEXT | Neighbourhood slug the listing was found under, e.g. `ensanche-juan-florez`. |
| `title` | TEXT | Listing title as shown on the card. |
| `price` | TEXT | Price string as shown, e.g. `395.000€`. Updated on every run — old prices logged to `price_history`. |
| `details` | TEXT | Summary line from the card, e.g. `3 hab. 106 m² Planta 5ª exterior con ascensor`. |
| `published` | TEXT | Raw date string from the detail page, e.g. `Anuncio actualizado el 26 de marzo`. Only populated on first discovery. |
| `description` | TEXT | Full listing description text. Only populated on first discovery. |
| `bathrooms` | INTEGER | Number of bathrooms, extracted from the detail page. |
| `usable_sqm` | INTEGER | Usable square metres (`m² útiles`), from the detail page. |
| `has_terrace` | INTEGER | 1 if the listing mentions a terrace, 0 otherwise. |
| `has_elevator` | INTEGER | 1 if the listing mentions an elevator (`con ascensor`), 0 otherwise. |
| `condition` | TEXT | Property condition, e.g. `Segunda mano/buen estado` or `Obra nueva`. |
| `heating` | TEXT | Heating type, e.g. `Calefacción individual: gas natural`. |
| `energy_rating` | TEXT | Energy certificate letter (A–G), extracted from the icon class on the detail page. |
| `community_fees` | TEXT | Community fees string, e.g. `120 €/mes`. |
| `price_per_sqm` | TEXT | Price per square metre string, e.g. `3.726 €/m²`. |
| `first_seen` | TEXT | ISO 8601 datetime when the listing was first discovered. Never updated after insert. |
| `last_seen` | TEXT | ISO 8601 datetime of the most recent run that found this listing still active on Idealista. |

---

## Table: `price_history`

Append-only log of price changes. A row is inserted whenever a known listing's price changes.

| Column | Type | Description |
|---|---|---|
| `url` | TEXT | References `listings.url` (not enforced by FK constraint). |
| `price` | TEXT | The **old** price at the time of change, e.g. `410.000€`. |
| `recorded_at` | TEXT | ISO 8601 datetime when the change was detected. |

---

## New listing detection

The scraper determines whether a listing is new using a simple URL membership check:

```
At startup:
  seen_ids = { all urls currently in listings.db }   ← loaded into memory

For each listing card scraped:
  if card.url NOT IN seen_ids:
      → NEW listing
         visit detail page → extract all fields
         INSERT full row into listings.db
         add url to seen_ids
  else:
      → KNOWN listing
         UPDATE price + last_seen only (no detail page visit)
         if new price ≠ stored price:
             INSERT old price into price_history
```

**"New" means:** the URL has never been seen before in this database. There is no date comparison — only URL presence.

**Implication:** if a listing is removed from Idealista (sold, expired) and later re-listed under a new URL, it will be treated as a completely new listing and fully re-scraped. If it re-appears under the same URL, it will simply update `last_seen` and price.

---

## Upsert behaviour summary

| Scenario | Detail page visited | Action |
|---|---|---|
| URL not in DB (new listing) | Yes | Full INSERT — all fields populated |
| URL already in DB, price unchanged | No | UPDATE `last_seen` only |
| URL already in DB, price changed | No | UPDATE `price` + `last_seen`; INSERT old price into `price_history` |

`published`, `description`, and all detail-page fields are only fetched on first discovery. They are not re-fetched on subsequent runs to keep the scraper fast.

---

## Useful queries

**All listings, most recently discovered first:**
```sql
SELECT title, price, details, neighbourhood, first_seen
FROM listings
ORDER BY first_seen DESC;
```

**Listings found in the last 7 days:**
```sql
SELECT title, price, neighbourhood, first_seen
FROM listings
WHERE first_seen >= datetime('now', '-7 days')
ORDER BY first_seen DESC;
```

**Listings no longer active (not seen in last 30 days):**
```sql
SELECT title, price, neighbourhood, last_seen
FROM listings
WHERE last_seen < datetime('now', '-30 days')
ORDER BY last_seen DESC;
```

**Count per neighbourhood:**
```sql
SELECT neighbourhood, COUNT(*) as total
FROM listings
GROUP BY neighbourhood
ORDER BY total DESC;
```

**Full price history for a listing:**
```sql
SELECT l.title, l.price as current_price, ph.price as old_price, ph.recorded_at
FROM price_history ph
JOIN listings l ON l.url = ph.url
WHERE ph.url = '/inmueble/110223106/'
ORDER BY ph.recorded_at DESC;
```

**All listings that have had a price change:**
```sql
SELECT l.title, l.price as current_price, ph.price as old_price, ph.recorded_at
FROM price_history ph
JOIN listings l ON l.url = ph.url
ORDER BY ph.recorded_at DESC;
```
