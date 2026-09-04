"""In-memory store standing in for the database (the real service uses Postgres)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    account_id: str
    is_admin: bool = False


@dataclass
class Store:
    accounts: dict = field(default_factory=dict)      # account_id -> {"balance_cents": int, "plan": str}
    invoices: dict = field(default_factory=dict)      # invoice_id -> {"account_id", "lines": [(unit_price, qty)], "status"}
    subscriptions: dict = field(default_factory=dict) # sub_id -> {"account_id", "status", "renews_at", "last_charge"}
    events_seen: set = field(default_factory=set)     # provider event ids we have already processed


STORE = Store()


def seed() -> None:
    STORE.accounts["acct_a"] = {"balance_cents": 0, "plan": "pro"}
    STORE.accounts["acct_b"] = {"balance_cents": 0, "plan": "team"}
    STORE.invoices["inv_1"] = {"account_id": "acct_a", "lines": [(19.99, 3), (4.50, 1)], "status": "open"}
    STORE.invoices["inv_2"] = {"account_id": "acct_b", "lines": [(120.00, 1)], "status": "paid"}
    STORE.subscriptions["sub_1"] = {"account_id": "acct_a", "status": "active", "renews_at": 0, "last_charge": None}
