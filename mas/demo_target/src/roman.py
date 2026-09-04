"""Convert between integers and Roman numerals (1..3999)."""

_TO_ROMAN = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (50, "L"),
    (10, "X"),
    (5, "V"),
    (1, "I"),
]

_FROM_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def int_to_roman(n):
    """Return the canonical Roman numeral for ``n`` (uses subtractive forms,
    e.g. 4 -> ``IV``, 9 -> ``IX``, 40 -> ``XL``, 900 -> ``CM``)."""
    if not 1 <= n <= 3999:
        raise ValueError("n must be in 1..3999")
    out = []
    for value, symbol in _TO_ROMAN:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


def roman_to_int(s):
    """Parse a Roman numeral (including subtractive forms) into an int."""
    total = 0
    prev = 0
    for ch in reversed(s.upper()):
        value = _FROM_ROMAN[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total
