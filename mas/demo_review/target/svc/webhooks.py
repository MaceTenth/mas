"""Payment-provider webhooks → account credits.

The provider signs each payload with HMAC-SHA256 and retries delivery (with the same
event id) until it receives a 2xx, for up to 3 days.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from .store import STORE

WEBHOOK_SECRET = b"whsec_test_only"


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook(payload: bytes, signature: str) -> dict:
    """Entry point for POST /webhooks/payments. Returns the HTTP body; 2xx unless ok is False."""
    if not verify_signature(payload, signature):
        return {"ok": False, "error": "bad signature"}
    event = json.loads(payload)
    kind = event.get("type")
    data = event.get("data", {})
    if kind == "payment.succeeded":
        acct = STORE.accounts.get(data["account_id"])
        if acct is None:
            return {"ok": False, "error": "unknown account"}
        acct["balance_cents"] += int(data["amount_cents"])
        for inv_id in data.get("invoice_ids", []):
            if inv_id in STORE.invoices:
                STORE.invoices[inv_id]["status"] = "paid"
    elif kind == "payment.failed":
        sub = STORE.subscriptions.get(data.get("subscription_id"))
        if sub:
            sub["status"] = "past_due"
    return {"ok": True}
