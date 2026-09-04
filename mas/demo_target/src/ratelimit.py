"""Sliding-window rate limiter."""
from collections import deque


class SlidingWindowLimiter:
    """Allow at most ``limit`` events per ``window`` seconds.

    ``allow(now)`` returns True and records the event if the caller is under
    the limit, considering only events strictly newer than ``now - window``.
    """

    def __init__(self, limit, window):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self._events = deque()

    def allow(self, now):
        while self._events and self._events[0] <= now - self.window:
            self._events.popleft()
        if len(self._events) > self.limit:
            return False
        self._events.append(now)
        return True

    def active_count(self, now):
        """Events still inside the window at time ``now``."""
        return sum(1 for t in self._events if t > now - self.window)
