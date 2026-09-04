import pytest
from roman import int_to_roman, roman_to_int


def test_simple_additive():
    assert int_to_roman(3) == "III"
    assert int_to_roman(1666) == "MDCLXVI"


def test_subtractive_forms():
    assert int_to_roman(4) == "IV"
    assert int_to_roman(9) == "IX"
    assert int_to_roman(40) == "XL"
    assert int_to_roman(90) == "XC"
    assert int_to_roman(400) == "CD"
    assert int_to_roman(900) == "CM"


def test_complex_number():
    assert int_to_roman(1994) == "MCMXCIV"
    assert int_to_roman(3999) == "MMMCMXCIX"


def test_out_of_range():
    with pytest.raises(ValueError):
        int_to_roman(0)


def test_roman_to_int_roundtrip():
    for n in (1, 4, 9, 14, 40, 90, 400, 900, 1994, 2426, 3999):
        assert roman_to_int(int_to_roman(n)) == n
