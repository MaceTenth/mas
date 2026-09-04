import pytest
from ratelimit import SlidingWindowLimiter


def test_allows_up_to_limit():
    rl = SlidingWindowLimiter(limit=3, window=10)
    assert rl.allow(0.0)
    assert rl.allow(1.0)
    assert rl.allow(2.0)


def test_rejects_over_limit():
    rl = SlidingWindowLimiter(limit=3, window=10)
    for t in (0.0, 1.0, 2.0):
        rl.allow(t)
    assert rl.allow(3.0) is False


def test_old_events_expire():
    rl = SlidingWindowLimiter(limit=2, window=10)
    assert rl.allow(0.0)
    assert rl.allow(1.0)
    assert rl.allow(5.0) is False
    assert rl.allow(11.5) is True  # the event at t=0.0 has left the window


def test_rejected_call_does_not_consume_slot():
    rl = SlidingWindowLimiter(limit=1, window=10)
    assert rl.allow(0.0)
    assert rl.allow(1.0) is False
    assert rl.allow(2.0) is False  # still blocked by t=0.0 only
    assert rl.allow(10.5) is True


def test_invalid_args():
    with pytest.raises(ValueError):
        SlidingWindowLimiter(0, 10)
