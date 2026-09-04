from csvlite import parse_line


def test_simple_fields():
    assert parse_line("a,b,c") == ["a", "b", "c"]


def test_empty_fields():
    assert parse_line("a,,c") == ["a", "", "c"]


def test_quoted_field_with_comma():
    assert parse_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_escaped_quotes_inside_quoted_field():
    assert parse_line('a,"say ""hi""",b') == ["a", 'say "hi"', "b"]


def test_quoted_field_only_escaped_quote():
    assert parse_line('""""') == ['"']
