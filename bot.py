"""SauceDemo shopping automation. Run with `python bot.py --help`."""

import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from playwright.sync_api import expect, sync_playwright


SITE = "https://www.saucedemo.com"


def money(text):
    """Parse a displayed dollar amount without floating point arithmetic."""
    match = re.fullmatch(r"(?:[^$]*\$)?(\d+\.\d{2})", text.strip())
    if not match:
        raise ValueError(f"Invalid displayed price: {text!r}")
    return Decimal(match.group(1))


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_input(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input.json must contain an object")
    items, customer = data.get("items"), data.get("customer")
    if not isinstance(items, list) or any(not isinstance(i, str) or not i.strip() for i in items):
        raise ValueError("items must be a list of nonempty product names")
    if not isinstance(customer, dict):
        raise ValueError("customer must contain first_name, last_name and zip")
    for key in ("first_name", "last_name", "zip"):
        if not isinstance(customer.get(key), str) or not customer[key].strip():
            raise ValueError(f"customer.{key} must be a nonempty string")
    return items, customer


def validate_totals(totals, expected):
    if totals["item_total"] != expected:
        raise ValueError(f"Item total mismatch: expected ${expected:.2f}, observed ${totals['item_total']:.2f}")


def select_products(items, catalog):
    """Match names case-insensitively; preserve missing input names for reporting."""
    selected, missing = [], []
    for requested in items:
        product = catalog.get(requested.casefold())
        if product is None:
            missing.append(requested)
        else:
            selected.append(product)
    return selected, missing


def save_acknowledgement(page, output):
    button = page.get_by_role("button", name="Generate PDF order", exact=True)
    expect(button).to_be_visible()
    with page.expect_download() as event:
        button.click()

    download = event.value
    failure = download.failure()
    if failure:
        raise ValueError(f"Acknowledgement download failed: {failure}")

    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"confirmation_{timestamp}_IST.pdf"
    destination = output / filename
    temporary = destination.with_suffix(".pdf.part")

    try:
        download.save_as(str(temporary))
        with temporary.open("rb") as pdf:
            if pdf.read(5) != b"%PDF-":
                raise ValueError("Acknowledgement download is not a PDF")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return filename

def shop(page, items, customer, username, password, output, result):
    page.goto(SITE, wait_until="domcontentloaded")
    page.locator('[data-test="username"]').fill(username)
    page.locator('[data-test="password"]').fill(password)
    page.locator('[data-test="login-button"]').click()
    inventory = page.locator('[data-test="inventory-list"]')
    login_error = page.locator('[data-test="error"]')
    expect(inventory.or_(login_error)).to_be_visible()
    if login_error.is_visible():
        raise ValueError("Login failed: " + login_error.inner_text())

    rows = inventory.locator('[data-test="inventory-item"]')
    expect(rows.first).to_be_visible()
    products, catalog = [], {}
    for index in range(rows.count()):
        row = rows.nth(index)
        name = row.locator('[data-test="inventory-item-name"]').inner_text()
        price = money(row.locator('[data-test="inventory-item-price"]').inner_text())
        products.append({"name": name, "description": row.locator('[data-test="inventory-item-desc"]').inner_text(), "price": float(price)})
        key = name.casefold()
        if key in catalog:
            raise ValueError(f"Ambiguous catalog product name: {name}")
        catalog[key] = (name, price, row)
    write_json(output / "products.json", products)

    selected, result["missing_items"] = select_products(items, catalog)

    # Quantity semantics are outside the currently approved scope.
    if len({p[0] for p in selected}) != len(selected):
        raise ValueError("Duplicate requested products are outside the current scope; use distinct item names")
    if not selected:
        raise ValueError("No requested products found; no order placed")

    for name, price, row in selected:
        row.get_by_role("button", name="Add to cart", exact=True).click()
        expect(row.get_by_role("button", name="Remove", exact=True)).to_be_visible()
        result["purchased_items"].append(name)

    page.locator('[data-test="shopping-cart-link"]').click()
    cart = page.locator('[data-test="inventory-item"]')
    expect(cart).to_have_count(len(selected))
    cart_names = cart.locator('[data-test="inventory-item-name"]').all_text_contents()
    if sorted(cart_names) != sorted(p[0] for p in selected):
        raise ValueError("Cart contents differ from the selected products")
    page.locator('[data-test="checkout"]').click()
    for key, selector in (("first_name", "firstName"), ("last_name", "lastName"), ("zip", "postalCode")):
        page.locator(f'[data-test="{selector}"]').fill(customer[key])
    page.locator('[data-test="continue"]').click()
    expect(page.locator('[data-test="subtotal-label"]')).to_be_visible()
    totals = {
        "item_total": money(page.locator('[data-test="subtotal-label"]').inner_text()),
        "tax": money(page.locator('[data-test="tax-label"]').inner_text()),
        "total": money(page.locator('[data-test="total-label"]').inner_text()),
    }
    result["order_totals"] = {key: float(value) for key, value in totals.items()}
    expected = sum((p[1] for p in selected), Decimal("0.00"))
    result["expected_item_total"] = float(expected)
    validate_totals(totals, expected)
    page.locator('[data-test="finish"]').click()
    expect(page.locator('[data-test="complete-header"]')).to_have_text("Thank you for your order!")
    expect(page.locator('[data-test="complete-text"]')).to_be_visible()
    result["confirmation_file"] = save_acknowledgement(page, output)


def run(args):
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = {"status": "failed", "order_totals": None, "expected_item_total": None,
              "missing_items": [], "purchased_items": [], "confirmation_file": None, "error": None}
    try:
        # Avoid presenting evidence from an earlier successful run as current evidence.
        for name in ("products.json", "confirmation.pdf"):
            (output / name).unlink(missing_ok=True)
        items, customer = read_input(Path(args.input))
        username, password = os.environ.get("SAUCE_USERNAME"), os.environ.get("SAUCE_PASSWORD")
        if not username or not password:
            raise ValueError("Set SAUCE_USERNAME and SAUCE_PASSWORD environment variables")
        with sync_playwright() as playwright:
            launch = {"headless": not args.headed}
            if args.browser_path:
                launch["executable_path"] = args.browser_path
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            if proxy:
                launch["proxy"] = {"server": proxy}
            browser = playwright.chromium.launch(**launch)
            try:
                page = browser.new_page(accept_downloads=True)
                expect.set_options(timeout=args.timeout_ms)
                page.set_default_timeout(args.timeout_ms)
                page.set_default_navigation_timeout(args.timeout_ms)
                shop(page, items, customer, username, password, output, result)
            finally:
                browser.close()
        result["status"] = "success"
    except Exception as error:
        # Browser diagnostics can include locator values; never persist credentials.
        message = f"{type(error).__name__}: {error}"
        for name in ("SAUCE_PASSWORD", "SAUCE_USERNAME"):
            value = os.environ.get(name)
            if value:
                message = message.replace(value, "[REDACTED]")
        result["error"] = message
    write_json(output / "result.json", result)
    print(f"{result['status']}: {output / 'result.json'}")
    return 0 if result["status"] == "success" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="input.json")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--browser-path", help="Optional system Chromium executable")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=60000, help="Maximum state wait; not a fixed sleep")
    args = parser.parse_args()
    if args.timeout_ms <= 0:
        parser.error("--timeout-ms must be positive")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
