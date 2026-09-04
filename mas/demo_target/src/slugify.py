"""Convert arbitrary text into URL-safe slugs."""
import re
import unicodedata


def slugify(text, max_len=64):
    """Return a lowercase, ascii, hyphen-separated slug of ``text``.

    Consecutive non-alphanumeric characters collapse into a single hyphen,
    and the result never starts or ends with a hyphen. Truncation to
    ``max_len`` must not leave a trailing hyphen.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    if len(text) > max_len:
        text = text[:max_len]
    return text
