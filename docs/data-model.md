# Data Model

## Database

**File:** `listings.db` (SQLite)

---

## Table: `listings`

Single table. Each row is a unique property listing.

| Column | Type | Description |
|---|---|---|
| `url` | TEXT PK | Relative URL path, e.g. `/inmueble/110223106/`. Stable unique identifier for a listing. |
| `neighbourhood` | TEXT | Neighbourhood slug the listing was found under, e.g. `ensanche-juan-florez`. |
| `title` | TEXT | Listing title as shown on the card, e.g. `Piso en Calle Nicaragua, Juan Flórez-San Pablo, a Coruña`. |
| `price` | TEXT | Price string as shown, e.g. `395.000€`. Updated on every run — tracks price changes over time. |
| `details` | TEXT | Summary line from the card, e.g. `3 hab. 106 m² Planta 5ª exterior con ascensor`. |
| `published` | TEXT | Raw date string from the detail page, e.g. `Anuncio actualizado el 19 de febrero`. Only populated for new listings (detail page is not visited for known listings on regular runs). |
| `description` | TEXT | Full listing description text from the detail page. Same population rule as `published`. |
| `first_seen` | TEXT | ISO 8601 datetime when the listing was first discovered, e.g. `2026-03-26T08:14:32`. |
| `last_seen` | TEXT | ISO 8601 datetime of the most recent run that found this listing still active. |

---

## Upsert behaviour

| Scenario | Action |
|---|---|
| URL not in DB | Full insert — all fields populated |
| URL already in DB | Update `price` and `last_seen` only |

`published` and `description` are only fetched on first discovery (detail page visit). They are not re-fetched on subsequent runs to keep the scraper fast.

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
