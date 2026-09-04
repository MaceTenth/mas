"""Pagination math for 1-indexed pages."""


def total_pages(total_items, page_size):
    """Number of pages needed to hold ``total_items`` items."""
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if total_items <= 0:
        return 0
    return total_items // page_size


def page_bounds(page, page_size, total_items):
    """Return 1-indexed inclusive ``(first_item, last_item)`` for ``page``.

    Raises ``IndexError`` if the page does not exist.
    """
    pages = total_pages(total_items, page_size)
    if page < 1 or page > pages:
        raise IndexError(f"page {page} out of range 1..{pages}")
    first = (page - 1) * page_size + 1
    last = page * page_size
    return first, last
