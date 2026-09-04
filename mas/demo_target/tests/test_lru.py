import pytest
from lru import LRUCache


def test_put_get_roundtrip():
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # "a" is LRU and must be evicted
    assert "a" not in c
    assert c.get("b") == 2 and c.get("c") == 3


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # "a" becomes most recently used
    c.put("c", 3)       # so "b" must be evicted, not "a"
    assert "b" not in c
    assert c.get("a") == 1 and c.get("c") == 3


def test_update_existing_key_refreshes():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)      # refreshes "a"
    c.put("c", 3)       # evicts "b"
    assert c.get("a") == 10
    assert "b" not in c


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
