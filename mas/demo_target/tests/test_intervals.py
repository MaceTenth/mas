from intervals import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_disjoint_stay_separate():
    assert merge_intervals([(1, 2), (4, 5)]) == [(1, 2), (4, 5)]


def test_overlapping_merge():
    assert merge_intervals([(1, 4), (2, 6)]) == [(1, 6)]


def test_touching_intervals_merge():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_unsorted_input():
    assert merge_intervals([(5, 7), (1, 3), (2, 4)]) == [(1, 4), (5, 7)]


def test_nested_interval():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]
