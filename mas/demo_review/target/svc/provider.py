"""Thin client for the payment provider's charge API."""
from __future__ import annotations

import time
import uuid


class TransientError(Exception):
    """Network blip / 5xx — safe to retry."""


class ProviderError(Exception):
    """4xx — the request itself was rejected (declined card, bad params)."""


def _provider_call(op: str, params: dict) -> dict:  # pragma: no cover — replaced by the SDK in production
    raise TransientError("provider unavailable")


def charge(account_id: str, amount_cents: int) -> dict | None:
    """Charge the account. Retries transient failures with backoff.

    Returns the provider's charge object on success.
    """
    idempotency_key = str(uuid.uuid4())
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return _provider_call("charge", {"account": account_id, "amount": amount_cents,
                                             "idempotency_key": idempotency_key})
        except TransientError as e:
            last_error = e
            time.sleep(0.05 * 2 ** attempt)
        except ProviderError as e:
            last_error = e
            break
    return None
