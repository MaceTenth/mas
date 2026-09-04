"""Merge overlapping or touching integer intervals."""


def merge_intervals(intervals):
    """Merge a list of ``(start, end)`` intervals.

    Input may be in any order. Intervals that overlap or merely touch
    (e.g. ``(1, 2)`` and ``(2, 3)``) are merged. Returns a sorted list
    of tuples.
    """
    if not intervals:
        return []
    ivs = list(intervals)
    merged = [list(ivs[0])]
    for start, end in ivs[1:]:
        last = merged[-1]
        if start < last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return [tuple(pair) for pair in merged]
