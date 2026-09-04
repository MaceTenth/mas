"""Minimal CSV line parser supporting quoted fields."""


def parse_line(line):
    """Parse one CSV line into a list of field strings.

    Rules:
    - Fields are separated by commas.
    - A field may be wrapped in double quotes; commas inside quotes are literal.
    - Inside a quoted field, a doubled quote ``""`` is an escaped literal quote.
    """
    fields = []
    current = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                in_quotes = False
            else:
                current.append(ch)
        else:
            if ch == '"':
                in_quotes = True
            elif ch == ",":
                fields.append("".join(current))
                current = []
            else:
                current.append(ch)
        i += 1
    fields.append("".join(current))
    return fields
