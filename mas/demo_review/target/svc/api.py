"""HTTP-facing functions for the billing API (framework glue lives elsewhere)."""
from __future__ import annotations

import csv
import io
import json

from .billing import invoice_total_cents
from .store import STORE, User


class Forbidden(Exception):
    pass


class NotFound(Exception):
    pass


def _authorize(user: User, account_id: str) -> None:
    if user.is_admin or user.account_id == account_id:
        return
    raise Forbidden(f"user {user.id} may not access account {account_id}")


def get_invoice(user: User, invoice_id: str) -> dict:
    inv = STORE.invoices.get(invoice_id)
    if inv is None:
        raise NotFound(invoice_id)
    _authorize(user, inv["account_id"])
    return {**inv, "total_cents": invoice_total_cents(inv["lines"])}


def list_invoices(user: User, account_id: str, cursor: int = 0, limit: int = 50) -> dict:
    _authorize(user, account_id)
    rows = sorted(i for i, inv in STORE.invoices.items() if inv["account_id"] == account_id)
    page = rows[cursor:cursor + limit]
    return {"invoices": page, "next_cursor": cursor + limit if len(rows) > cursor + limit else None}


def export_invoices(user: User, account_id: str, fmt: str = "csv") -> str:
    """Bulk export for the finance dashboard. fmt: csv | json."""
    rows = [{"id": i, **inv, "total_cents": invoice_total_cents(inv["lines"])}
            for i, inv in STORE.invoices.items() if inv["account_id"] == account_id]
    if fmt == "json":
        return json.dumps(rows, default=str)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "status", "total_cents"])
    for r in rows:
        w.writerow([r["id"], r["status"], r["total_cents"]])
    return buf.getvalue()
