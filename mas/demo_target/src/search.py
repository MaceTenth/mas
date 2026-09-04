"""Binary search helpers over sorted lists."""


def find_insert_pos(arr, target):
    """Return the leftmost index where ``target`` can be inserted into the
    sorted list ``arr`` while keeping it sorted (like ``bisect.bisect_left``).

    If ``target`` already exists, the returned index is that of its first
    occurrence.
    """
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def contains(arr, target):
    """True if ``target`` is present in sorted list ``arr``."""
    pos = find_insert_pos(arr, target)
    return pos < len(arr) and arr[pos] == target
