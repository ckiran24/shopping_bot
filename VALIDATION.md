# Validation

## Actual assignment runs

Both `standard_user` and `performance_glitch_user` completed against the live
https://www.saucedemo.com site using the same bot code and the supplied `input.json`.
Credentials were passed through environment variables, not embedded in source.
TLS verification remained enabled; no fixed sleeps were used.

Each run:

- Extracted all six products with descriptions and numeric prices.
- Reported `Sauce Labs Water Bottle` as missing without guessing a replacement.
- Added `Sauce Labs Backpack` and `Sauce Labs Onesie`.
- Verified subtotal **37.98**, and read tax **3.04** and total **41.02**.
- Reached the actual thank-you page and saved `confirmation.pdf`.
- Wrote `result.json` with `status: success` and no error.

Outputs are in `outputs/standard_user/` and `outputs/performance_glitch_user/`.
The PDF text was checked for the actual order confirmation. Artifacts belong to
these current runs, not a fabricated or simulated checkout.

## Additional live tests

Three opt-in browser tests passed:

- Case-insensitive names plus a missing water bottle completed checkout.
- An all-missing list produced a failed result with all missing names, no totals,
  and no confirmation PDF.
- A deliberately injected subtotal of 0.01 raised a mismatch while the browser
  remained on the overview page with Finish still available. This test exercises
  the protection; it is not an observed pricing defect on SauceDemo.

## Unit tests

Eleven standard-library tests passed: displayed monetary amounts, malformed prices,
decimal addition, subtotal mismatch, assignment input, malformed customer, missing
credentials with stale-evidence removal, missing input reporting, case-insensitive
matches with missing items, all-missing reporting, and refusal to guess similar names.

