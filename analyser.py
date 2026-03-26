"""
Idealista analyser — queries listings.db and produces basic data analysis.

Usage:
  python analyser.py              # summary + listings from last 7 days
  python analyser.py --days 30    # listings from last 30 days
  python analyser.py --all        # all listings
"""

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta

DB_FILE = "listings.db"


# ── Helpers ───────────────────────────────────────────────────────────────────

def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def parse_price(price_str):
    """'295.000€' → 295000"""
    if not price_str:
        return None
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else None


def parse_price_per_sqm(val):
    """'2.921 €/m²' → 2921"""
    if not val:
        return None
    digits = re.sub(r"[^\d]", "", val.split("€")[0])
    return int(digits) if digits else None


def avg(lst):
    lst = [x for x in lst if x is not None]
    return sum(lst) / len(lst) if lst else None


def fmt_price(val):
    if val is None:
        return "N/A"
    return f"{val:,.0f}€".replace(",", ".")


def fmt_sqm(val):
    return f"{val:,.0f} €/m²".replace(",", ".") if val else "N/A"


def bar(value, max_value, width=20):
    filled = int(round(value / max_value * width)) if max_value else 0
    return "█" * filled + "░" * (width - filled)


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch(days=None):
    query = "SELECT * FROM listings"
    params = ()
    if days is not None:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query += " WHERE first_seen >= ?"
        params = (cutoff,)
    query += " ORDER BY first_seen DESC"
    with db_connect() as conn:
        return conn.execute(query, params).fetchall()


# ── Sections ──────────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def print_overview(rows):
    section("OVERVIEW")
    prices   = [parse_price(r["price"]) for r in rows]
    ppm      = [parse_price_per_sqm(r["price_per_sqm"]) for r in rows]
    valid_p  = [p for p in prices if p]
    valid_pp = [p for p in ppm if p]

    print(f"  Total listings : {len(rows)}")
    if valid_p:
        print(f"  Price range    : {fmt_price(min(valid_p))} – {fmt_price(max(valid_p))}")
        print(f"  Average price  : {fmt_price(avg(valid_p))}")
        print(f"  Median price   : {fmt_price(sorted(valid_p)[len(valid_p)//2])}")
    if valid_pp:
        print(f"  Avg €/m²       : {fmt_sqm(avg(valid_pp))}")


def print_by_neighbourhood(rows):
    section("BY NEIGHBOURHOOD")
    by_n = {}
    for r in rows:
        n = r["neighbourhood"]
        by_n.setdefault(n, []).append(r)

    max_count = max(len(v) for v in by_n.values())
    for n, listings in sorted(by_n.items(), key=lambda x: -len(x[1])):
        prices = [parse_price(r["price"]) for r in listings]
        avg_p  = avg(prices)
        print(f"\n  {n}")
        print(f"  {bar(len(listings), max_count)} {len(listings)} listings")
        print(f"  Avg price: {fmt_price(avg_p)}  |  "
              f"Range: {fmt_price(min(p for p in prices if p))} – {fmt_price(max(p for p in prices if p))}")


def print_price_distribution(rows):
    section("PRICE DISTRIBUTION")
    buckets = [
        (0,       200_000, "< 200k"),
        (200_000, 250_000, "200k–250k"),
        (250_000, 300_000, "250k–300k"),
        (300_000, 350_000, "300k–350k"),
        (350_000, 400_000, "350k–400k"),
        (400_000, 450_000, "400k–450k"),
    ]
    counts = Counter()
    for r in rows:
        p = parse_price(r["price"])
        if p:
            for lo, hi, label in buckets:
                if lo <= p < hi:
                    counts[label] += 1
                    break

    max_count = max(counts.values()) if counts else 1
    for _, _, label in buckets:
        c = counts.get(label, 0)
        print(f"  {label:12s}  {bar(c, max_count)} {c}")


def print_features(rows):
    section("KEY FEATURES")
    total = len(rows)

    with_elevator = sum(1 for r in rows if r["has_elevator"])
    with_terrace  = sum(1 for r in rows if r["has_terrace"])
    print(f"  Elevator       : {with_elevator}/{total} ({100*with_elevator//total}%)")
    print(f"  Terrace        : {with_terrace}/{total} ({100*with_terrace//total}%)")

    baths = [r["bathrooms"] for r in rows if r["bathrooms"]]
    if baths:
        print(f"  Bathrooms avg  : {avg(baths):.1f}  (range: {min(baths)}–{max(baths)})")

    print()
    print("  Condition breakdown:")
    conditions = Counter(r["condition"] for r in rows if r["condition"])
    for cond, count in conditions.most_common():
        print(f"    {bar(count, total, 15)} {count:3d}  {cond}")

    print()
    print("  Energy rating:")
    ratings = Counter(r["energy_rating"] for r in rows if r["energy_rating"])
    for rating in sorted(ratings):
        count = ratings[rating]
        print(f"    {rating}  {bar(count, total, 15)} {count}")

    print()
    print("  Heating:")
    heats = Counter(r["heating"] for r in rows if r["heating"])
    for heat, count in heats.most_common(5):
        label = heat[:45] + "…" if len(heat) > 45 else heat
        print(f"    {bar(count, total, 10)} {count:3d}  {label}")


def print_best_value(rows, n=10):
    section(f"BEST VALUE (lowest €/m²)")
    ranked = sorted(
        [r for r in rows if parse_price_per_sqm(r["price_per_sqm"])],
        key=lambda r: parse_price_per_sqm(r["price_per_sqm"])
    )
    for r in ranked[:n]:
        elev    = "lift" if r["has_elevator"] else "no lift"
        terrace = "terrace" if r["has_terrace"] else ""
        tags    = ", ".join(filter(None, [elev, terrace]))
        print(f"\n  {r['price_per_sqm']:12s}  {r['price']}")
        print(f"  {r['title']}")
        print(f"  {r['details']}  |  {tags}")
        print(f"  https://www.idealista.com{r['url']}")


def print_recently_added(rows, n=10):
    section(f"MOST RECENTLY ADDED (last {n})")
    for r in rows[:n]:
        print(f"\n  {r['first_seen'][:10]}  {r['price']:>12}  {r['title']}")
        print(f"  {r['details']}")
        print(f"  https://www.idealista.com{r['url']}")


def export_json(rows, filename="analysis.json"):
    output = [dict(r) for r in rows]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return filename


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=7)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    days = None if args.all else args.days
    rows = fetch(days)
    label = "all listings" if days is None else f"listings from last {days} day(s)"

    print(f"\n{'='*60}")
    print(f"  IDEALISTA ANALYSIS — {label.upper()}")
    print(f"{'='*60}")

    if not rows:
        print("  No listings found.")
        return

    print_overview(rows)
    print_by_neighbourhood(rows)
    print_price_distribution(rows)
    print_features(rows)
    print_best_value(rows)
    print_recently_added(rows)

    filename = export_json(rows)
    print(f"\n{'─'*60}")
    print(f"  Exported {len(rows)} listings to {filename}")


if __name__ == "__main__":
    main()
