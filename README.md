# SauceDemo shopping bot

Python and Playwright automation to create a shopping bot.
The bot logs in, extracts the catalog, adds requested products, checks the
checkout subtotal, finishes the order, and saves a confirmation PDF.

## Install and run

Use Python 3.12 or newer, from the repository directory:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

Set `SAUCE_USERNAME` and `SAUCE_PASSWORD` in your .env file.
settings using the test credentials printed on https://www.saucedemo.com.
Use `standard_user` for the assignment run. Change only `SAUCE_USERNAME` to
`performance_glitch_user` to exercise the slow login.

```sh
.venv/bin/python bot.py --input input.json --output-dir outputs/standard
```

For this machine, the existing Chromium is usable with
`--browser-path /usr/bin/chromium`. The bot respects `HTTPS_PROXY` when supplied.
The browser must trust the environment's supplied proxy CA; TLS checks are never
disabled by the bot. `--headed` enables a visible browser on machines with a display.
The configurable `--timeout-ms` defaults to 60000 milliseconds per state wait;
it is a maximum wait, never a fixed sleep.

`input.json` contains the assignment example, including the nonexistent water
bottle. Product names match by Unicode case folding: capitalization may differ,
but spelling must match. Missing names are recorded exactly as requested; the bot
does not invent substitutes. Repeated item names and quantities are outside the
currently agreed scope and produce an explicit error rather than silently deciding
quantity semantics.

## Outputs and failures

Each output directory contains:

- `products.json`: the complete catalog, with name, description, and numeric price.
- `result.json`: status, observed order totals, expected item total, missing items,
  selected cart items (`purchased_items`), confirmation filename, and failure error.
- `confirmation.pdf`: the actual confirmation page, produced only after successful checkout.

The expected subtotal sums only products successfully added to the cart, using
decimal arithmetic. Tax and final total are read from the page, rather than
calculated using an assumed tax rate. A mismatch fails before the Finish button
is clicked. The process exits 0 on success and 1 on a reported failure.
`purchased_items` records verified cart additions; a failed run does not imply an
order was placed. Order completion followed by PDF failure is reported as failed;
do not automatically retry checkout against a real payment site.

If every requested product is missing (or the shopping list is empty), the bot
records all missing names and fails before checkout. It does not place an empty order.

Use a separate output directory per run to retain evidence. Reusing a directory
replaces its `result.json` and clears old catalog/PDF evidence before starting.
Filesystem errors that prevent writing output are surfaced to the terminal.
Credentials are read only from environment variables and redacted from saved
exception messages. Do not commit real credentials or customer information.

## Tests

```sh
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

These tests cover decimal amounts, mismatch failure, input validation, and failure
reporting. Actual browser validation and its output artifacts are recorded in
`VALIDATION.md`; unit tests alone do not establish live checkout readiness.

Opt-in live checks (these place test orders on SauceDemo):

```sh
SAUCE_BROWSER_PATH=/usr/bin/chromium .venv/bin/python -m unittest discover -s tests/live -v
```

# Run the standard user with a visible browser
```sh
.\.venv\Scripts\python.exe bot.py --headed --output-dir outputs/standard
```

Omit `SAUCE_BROWSER_PATH` to use Playwright's installed Chromium. The live test
harness uses `SAUCE_PASSWORD` if set; otherwise it reads the public test password
from the homepage without printing or saving it. The production bot always reads
credentials from environment variables. In this cloud environment, live browser
commands need execution outside the filesystem sandbox so Chromium can initialize
its NSS trust database. The supplied proxy CA trust change was explicitly approved.

## Extending to 40 websites

Separate the common workflow and result schema from a small adapter for each site:
login, catalog extraction, cart manipulation, checkout totals, and confirmation.
Keeping the input, results, monetary checks, orchestraction common;Use site-specific 
locators and readiness conditions instead of a universal selector
guessing strategy. Maintain contract tests for each adapter, isolate credentials
and browser sessions per site, and record structured failures so a change on one
site does not hide failures on the others. Real purchase sites also need explicit
authorization, an order idempotency strategy, and recovery rules before retries.


# Verify results
Verified assignment outputs are retained in `outputs/standard_user/` and
`outputs/performance_glitch_user/` and included in the submission ZIP.
