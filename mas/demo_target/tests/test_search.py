from search import find_insert_pos, contains


def test_empty_list():
    assert find_insert_pos([], 5) == 0


def test_insert_position_between_elements():
    assert find_insert_pos([1, 3, 5], 4) == 2


def test_leftmost_position_for_duplicates():
    assert find_insert_pos([1, 2, 2, 2, 3], 2) == 1


def test_target_smaller_and_larger_than_all():
    assert find_insert_pos([2, 4, 6], 1) == 0
    assert find_insert_pos([2, 4, 6], 7) == 3


def test_contains_present_and_absent():
    assert contains([1, 2, 2, 3], 2) is True
    assert contains([1, 2, 2, 3], 5) is False
    assert contains([], 1) is False
