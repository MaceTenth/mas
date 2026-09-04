import pytest
from pagination import total_pages, page_bounds


def test_exact_division():
    assert total_pages(10, 5) == 2


def test_partial_last_page_counts():
    assert total_pages(10, 3) == 4


def test_zero_items():
    assert total_pages(0, 10) == 0


def test_first_page_bounds():
    assert page_bounds(1, 3, 10) == (1, 3)


def test_last_page_is_clamped_to_total():
    assert page_bounds(4, 3, 10) == (10, 10)


def test_out_of_range_page_raises():
    with pytest.raises(IndexError):
        page_bounds(5, 3, 10)
