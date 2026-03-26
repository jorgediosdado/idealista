"""
Quick test to check if Fotocasa can be scraped.
Run: python test_fotocasa.py
"""
from playwright.sync_api import sync_playwright
import time

URL = "https://www.fotocasa.es/es/comprar/viviendas/a-coruna-capital/todas-las-zonas/l"

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
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        window.chrome = { runtime: {} };
    """)

    page = context.new_page()
    print(f"Loading {URL} ...")
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)

    body = page.inner_text("body").lower()

    # Check for bot detection
    if any(k in body for k in ["captcha", "robot", "blocked", "access denied"]):
        print("BLOCKED — bot detection triggered")
    else:
        print("Page loaded OK")

    # Try to find listing cards
    selectors = [
        "article",
        "[class*='listing']",
        "[class*='PropertyCard']",
        "[data-testid*='property']",
        "li[class*='re-']",
    ]
    for sel in selectors:
        cards = page.query_selector_all(sel)
        if cards:
            print(f"  Found {len(cards)} elements matching '{sel}'")
            # Print text of first card
            print(f"  First card text: {cards[0].inner_text()[:200].strip()}")
            break
    else:
        print("  No listing cards found with known selectors")
        print(f"  Page title: {page.title()}")

    page.screenshot(path="fotocasa_test.png")
    print("Screenshot saved to fotocasa_test.png")

    input("Press Enter to close...")
    browser.close()
