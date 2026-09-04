"""A fixed-capacity least-recently-used (LRU) cache."""
from collections import OrderedDict


class LRUCache:
    """LRU cache: ``get`` and ``put`` both count as "use".

    When capacity is exceeded, the least recently used entry is evicted.
    """

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        """Return the value for ``key`` and mark it as most recently used."""
        if key not in self._data:
            return default
        return self._data[key]

    def put(self, key, value):
        """Insert or update ``key``, evicting the LRU entry if over capacity."""
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=True)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data
