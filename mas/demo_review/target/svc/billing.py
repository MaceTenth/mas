"""Invoice math and subscription renewals."""
from __future__ import annotations

import time

from .provider import charge
from .store import STORE

RENEWAL_PERIOD_S = 30 * 24 * 3600


def line_total_cents(unit_price: float, quantity: int) -> int:
    """Prices are stored as decimal strings in the DB and arrive here as floats from the ORM."""
    return int(unit_price * quantity * 100)


def invoice_total_cents(lines: list[tuple[float, int]]) -> int:
    return sum(line_total_cents(p, q) for p, q in lines)


def renew(sub_id: str, *, now: float | None = None) -> dict:
    """Charge the account for the next period and roll the subscription forward."""
    now = time.time() if now is None else now
    sub = STORE.subscriptions[sub_id]
    acct = STORE.accounts[sub["account_id"]]
    amount = 2900 if acct["plan"] == "pro" else 9900
    result = charge(sub["account_id"], amount)
    sub["last_charge"] = result
    sub["status"] = "active"
    sub["renews_at"] = now + RENEWAL_PERIOD_S
    return sub
