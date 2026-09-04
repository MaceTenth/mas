from slugify import slugify


def test_basic():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_collapses_to_single_hyphen():
    assert slugify("Hello,  World!!") == "hello-world"


def test_no_leading_or_trailing_hyphens():
    assert slugify("  --Hello--  ") == "hello"


def test_unicode_transliteration():
    assert slugify("Crème Brûlée") == "creme-brulee"


def test_truncation_has_no_trailing_hyphen():
    assert slugify("aaaa bbbb", max_len=5) == "aaaa"
