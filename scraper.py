"""
Idealista scraper — collects all listings matching the configured filters
and persists them to listings.db. Run daily via Task Scheduler.

Config: config.json (neighbourhoods, max_price, min_sqm)
Output: listings.db
"""

from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import os
import random
import re
import sqlite3
import time

CONFIG_FILE = "config.json"
DB_FILE     = "listings.db"
BASE_URL    = "https://www.idealista.com"
SORT        = "?ordenado-por=fecha-publicacion-desc"
TEST_LIMIT  = None   # set to 5 for test mode
MAX_PAGES   = 3      # max pages to check on regular runs


# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


ROOMS_FILTERS = {
    2: "de-dos-dormitorios,de-tres-dormitorios,de-cuatro-cinco-habitaciones-o-mas",
    3: "de-tres-dormitorios,de-cuatro-cinco-habitaciones-o-mas",
    4: "de-cuatro-cinco-habitaciones-o-mas",
}

def build_filters(cfg):
    parts = [
        f"con-precio-hasta_{cfg['max_price']}",
        f"metros-cuadrados-mas-de_{cfg['min_sqm']}",
    ]
    if cfg.get("min_rooms") and cfg["min_rooms"] in ROOMS_FILTERS:
        parts.append(ROOMS_FILTERS[cfg["min_rooms"]])
    return ",".join(parts)


def neighbourhood_base_url(neighbourhood, filters):
    return f"{BASE_URL}/venta-viviendas/a-coruna/{neighbourhood}/{filters}/"


def page_url(neighbourhood, filters, page_num):
    base = neighbourhood_base_url(neighbourhood, filters)
    if page_num == 1:
        return base + SORT
    return base + f"pagina-{page_num}.htm{SORT}"


# ── Database ──────────────────────────────────────────────────────────────────

def db_connect():
    return sqlite3.connect(DB_FILE)


NEW_COLUMNS = [
    ("bathrooms",      "INTEGER"),
    ("usable_sqm",     "INTEGER"),
    ("has_terrace",    "INTEGER"),
    ("has_elevator",   "INTEGER"),
    ("condition",      "TEXT"),
    ("heating",        "TEXT"),
    ("energy_rating",  "TEXT"),
    ("community_fees", "TEXT"),
    ("price_per_sqm",  "TEXT"),
]

def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                url           TEXT PRIMARY KEY,
                neighbourhood TEXT,
                title         TEXT,
                price         TEXT,
                details       TEXT,
                published     TEXT,
                description   TEXT,
                first_seen    TEXT,
                last_seen     TEXT
            )
        """)
        # Migrate: add new columns if they don't exist yet
        existing = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
        for col, col_type in NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")


def load_seen_ids():
    with db_connect() as conn:
        return {row[0] for row in conn.execute("SELECT url FROM listings")}


def is_first_run():
    if not os.path.exists(DB_FILE):
        return True
    with db_connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0


def upsert_listing(entry, neighbourhood):
    now = datetime.now().isoformat()
    with db_connect() as conn:
        exists = conn.execute(
            "SELECT url FROM listings WHERE url = ?", (entry["url"],)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE listings SET last_seen = ?, price = ? WHERE url = ?",
                (now, entry.get("price"), entry["url"]),
            )
        else:
            conn.execute(
                """INSERT INTO listings (
                       url, neighbourhood, title, price, details, published, description,
                       bathrooms, usable_sqm, has_terrace, has_elevator,
                       condition, heating, energy_rating, community_fees, price_per_sqm,
                       first_seen, last_seen
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["url"], neighbourhood, entry.get("title"),
                    entry.get("price"), entry.get("details"),
                    entry.get("published"), entry.get("description"),
                    entry.get("bathrooms"), entry.get("usable_sqm"),
                    entry.get("has_terrace"), entry.get("has_elevator"),
                    entry.get("condition"), entry.get("heating"),
                    entry.get("energy_rating"), entry.get("community_fees"),
                    entry.get("price_per_sqm"),
                    now, now,
                ),
            )


# ── Browser helpers ───────────────────────────────────────────────────────────

def pause(min_s=3, max_s=7):
    time.sleep(random.uniform(min_s, max_s))


def load_page(page, url):
    print(f"  Loading {url} ...")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    pause(5, 9)
    page.screenshot(path="screenshot.png", full_page=False)


def get_detail(detail_page, url):
    """Visit a listing detail page and extract all available fields."""
    empty = {
        "published": None, "description": None,
        "bathrooms": None, "usable_sqm": None,
        "has_terrace": None, "has_elevator": None,
        "condition": None, "heating": None,
        "energy_rating": None, "community_fees": None,
        "price_per_sqm": None,
    }
    try:
        pause(3, 8)
        detail_page.goto(BASE_URL + url, wait_until="domcontentloaded", timeout=20000)
        pause(2, 4)

        # Published date
        published = None
        for selector in [".stats-text", "[class*='date']", "time"]:
            el = detail_page.query_selector(selector)
            if el:
                text = el.inner_text().strip()
                if text:
                    published = text
                    break

        # Description
        description = None
        for selector in [".comment", "[class*='description']", ".adCommentsContainer"]:
            el = detail_page.query_selector(selector)
            if el:
                text = el.inner_text().strip()
                if text:
                    description = text
                    break

        # Feature list items — all detail fields live here
        feature_items = [
            el.inner_text().strip()
            for el in detail_page.query_selector_all("div.details-property_features li")
        ]
        features_text = "\n".join(feature_items).lower()

        bathrooms  = None
        usable_sqm = None
        condition  = None
        heating    = None
        has_terrace  = 0
        has_elevator = 0

        for item in feature_items:
            low = item.lower()
            # Bathrooms
            if "baño" in low and bathrooms is None:
                m = re.search(r"(\d+)\s*baño", low)
                if m:
                    bathrooms = int(m.group(1))
            # Usable sqm
            if "útiles" in low and usable_sqm is None:
                m = re.search(r"(\d+)\s*m²\s*útiles", low)
                if m:
                    usable_sqm = int(m.group(1))
            # Terrace
            if "terraza" in low:
                has_terrace = 1
            # Elevator
            if "con ascensor" in low:
                has_elevator = 1
            # Condition
            if ("segunda mano" in low or "obra nueva" in low) and condition is None:
                condition = item
            # Heating
            if "calefacción" in low and heating is None:
                heating = item

        # Energy rating — from icon class e.g. "icon-energy-c-d" → "C"
        energy_rating = None
        el = detail_page.query_selector("[class*='icon-energy-']")
        if el:
            cls = el.get_attribute("class") or ""
            m = re.search(r"icon-energy-([a-g])", cls, re.IGNORECASE)
            if m:
                energy_rating = m.group(1).upper()

        # Community fees — "Gastos de comunidad 100 €/mes"
        community_fees = None
        for el in detail_page.query_selector_all(".flex-feature-details"):
            text = el.inner_text()
            if "comunidad" in text.lower():
                m = re.search(r"(\d[\d.,]+\s*€/mes)", text)
                if m:
                    community_fees = m.group(1)
                break

        # Price per sqm
        price_per_sqm = None
        el = detail_page.query_selector(".squaredmeterprice")
        if el:
            spans = el.query_selector_all(".flex-feature-details")
            if len(spans) >= 2:
                price_per_sqm = spans[1].inner_text().strip()

        return {
            "published": published, "description": description,
            "bathrooms": bathrooms, "usable_sqm": usable_sqm,
            "has_terrace": has_terrace, "has_elevator": has_elevator,
            "condition": condition, "heating": heating,
            "energy_rating": energy_rating, "community_fees": community_fees,
            "price_per_sqm": price_per_sqm,
        }
    except Exception as e:
        print(f"  Could not fetch detail for {url}: {e}")
        return empty


def scrape_cards(page):
    """Extract basic fields from all listing cards on the current page."""
    items = page.query_selector_all("article.item")
    if TEST_LIMIT:
        items = items[:TEST_LIMIT]
    results = []
    for item in items:
        try:
            title   = item.query_selector(".item-link")
            price   = item.query_selector(".item-price")
            details = item.query_selector(".item-detail-char")
            link_el = item.query_selector("a.item-link")
            results.append({
                "title":   title.inner_text().strip() if title else None,
                "price":   price.inner_text().strip() if price else None,
                "details": details.inner_text().strip() if details else None,
                "url":     link_el.get_attribute("href") if link_el else None,
            })
        except Exception as e:
            print(f"  Error parsing card: {e}")
    return results


# ── Scraping logic ────────────────────────────────────────────────────────────

def scrape_neighbourhood(page, detail_page, seen_ids, neighbourhood, filters, first_run):
    """Scrape one neighbourhood. Paginate on first run, page 1 only on subsequent runs."""
    new_count = 0
    page_num  = 1

    while True:
        load_page(page, page_url(neighbourhood, filters, page_num))

        if "captcha" in page.inner_text("body").lower():
            print("  [BLOCKED] DataDome challenge detected.")
            return new_count

        cards = scrape_cards(page)
        if not cards:
            print(f"  Page {page_num}: no listings, stopping.")
            break

        print(f"  Page {page_num}: {len(cards)} listing(s)")

        new_on_page = 0
        for entry in cards:
            url_path = entry["url"]
            if not url_path:
                continue
            if url_path not in seen_ids:
                print(f"    [NEW] {entry['title']}")
                detail = get_detail(detail_page, url_path)
                upsert_listing({**entry, **detail}, neighbourhood)
                seen_ids.add(url_path)
                new_count += 1
                new_on_page += 1
            else:
                upsert_listing(entry, neighbourhood)  # update price + last_seen

        # Stop if all listings on this page are already known
        if new_on_page == 0:
            print(f"  No new listings on page {page_num}, stopping.")
            break

        # On regular runs cap at MAX_PAGES; first run goes until exhausted
        if not first_run and page_num >= MAX_PAGES:
            print(f"  Reached page limit ({MAX_PAGES}), stopping.")
            break

        page_num += 1

    return new_count


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    cfg     = load_config()
    filters = build_filters(cfg)
    init_db()
    first_run = is_first_run()
    seen_ids  = load_seen_ids()

    print(f"Config: max_price={cfg['max_price']}€, min_sqm={cfg['min_sqm']}m², "
          f"{len(cfg['neighbourhoods'])} neighbourhood(s)")
    print(f"Mode: {'FIRST RUN' if first_run else 'regular'} | DB: {len(seen_ids)} known listing(s)")
    if TEST_LIMIT:
        print(f"TEST MODE: capped at {TEST_LIMIT} listings per page\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        page        = context.new_page()
        detail_page = context.new_page()
        total_new   = 0

        for neighbourhood in cfg["neighbourhoods"]:
            print(f"\n--- {neighbourhood} ---")
            new_count = scrape_neighbourhood(
                page, detail_page, seen_ids, neighbourhood, filters, first_run
            )
            total_new += new_count
            pause(4, 10)

        browser.close()

    print(f"\nDone. {total_new} new listing(s) added to {DB_FILE}.")


if __name__ == "__main__":
    run()
