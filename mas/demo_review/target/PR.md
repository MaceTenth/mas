# PR #207 — billing: payment webhooks, invoice export, subscription renewals

**Author:** billing team · **Files:** `svc/webhooks.py`, `svc/api.py`, `svc/billing.py`, `svc/provider.py`, `svc/store.py`

## Why
We are moving off the legacy billing vendor. This PR adds the three pieces the new provider needs:
webhook handling (payments credit the account and mark invoices paid), a bulk invoice export for the
finance dashboard, and the monthly renewal job.

## What changed
- `webhooks.py` — verifies the provider's HMAC signature and applies `payment.succeeded` /
  `payment.failed` events. The provider retries any delivery that does not get a 2xx (same event id) for up to 3 days.
- `api.py` — `get_invoice`, `list_invoices` (cursor pagination) and the new `export_invoices` (csv/json)
  used by the finance dashboard.
- `billing.py` — invoice totals in cents from the ORM's float prices; `renew()` charges the account and
  rolls the subscription forward. Runs from the nightly job for every subscription due.
- `provider.py` — `charge()` with retry + backoff on transient errors and an idempotency key.
- `store.py` — in-memory stand-in for the DB in this sandbox.

## Testing
Exercised end to end in the sandbox with the provider's test events; totals matched the legacy vendor
for the sample invoices. Automated tests will land with the follow-up PR that wires the framework.

## Review question
List every bug in this change that would affect production — correctness, money, or security. Ignore style.
For each: where it is, one concrete failing scenario, and the fix.
