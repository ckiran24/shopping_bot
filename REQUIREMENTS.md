## Explicit requirements

- Use Python and Playwright against https://www.saucedemo.com.
- Read credentials from environment variables; log in as `standard_user`.
- Support `performance_glitch_user`, including its slow login, without code changes.
- Collect every product's name, description, and numeric price into `products.json`.
- Read item names and customer `first_name`, `last_name`, and `zip` from `input.json`.
- Report nonexistent items in `result.json` and continue with the remaining items.
- Read item total, tax, and total from the checkout overview.
- Validate the item total against collected prices; fail on mismatch.
- Finish the order and save a confirmation screenshot or PDF.
- Write `result.json` with `success` or `failed`, order totals, missing items,
  and an error message on failure.
- Wait for required page states; do not use fixed sleeps.
- Include running instructions and a short explanation of changes needed for 40 sites.
- Supply a GitHub repository or zip and output files from one actual run.

## Confirmed interim decisions

- The expected subtotal includes only products actually added to the cart.
- Duplicate-name behavior is outside scope for now; no quantity behavior is inferred.
- Product-name matching ignores capitalization but does not guess different spellings.
- Missing products are reported and processing continues with valid products.

## Confirmed empty-order decision

- When every requested product is missing, report failure and all missing names
  before checkout; do not place an empty order.

## Confirmed user choices

- Confirmation evidence: PDF.
- Credential variable names: `SAUCE_USERNAME` and `SAUCE_PASSWORD`.

## Current validation evidence

- The checkout was initially empty; no existing application code was present.
- Python and Playwright are installed in the current machine.
- The existing system Chromium at `/usr/bin/chromium` successfully launched
  through Playwright and passed a local browser interaction check.
- SauceDemo access and the Chromium download were blocked by the egress policy.
- Required domain additions were saved in the environment configuration draft:
  `www.saucedemo.com` and `cdn.playwright.dev`. A saved draft does not apply them
  to the current machine.
- SauceDemo subsequently responded successfully to a verified Python HTTPS request.
- Explicitly authorized adding the supplied proxy CA to Chromium's trust
  store. It was already present under another nickname; Chromium must initialize
  its NSS database outside the filesystem sandbox for verified live access.
- Eleven unit tests and three additional live browser tests passed. Actual
  standard-user and performance-glitch-user runs each extracted six products,
  reported the missing water bottle, checked out the backpack and onesie, and saved
  JSON outputs and a confirmation PDF.
- Both runs read subtotal 37.98, tax 3.04, and total 41.02 from the website.
