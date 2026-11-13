"""Parsing of HTML form fields and query strings, shared by the controllers.

Browsers submit an untouched <select> or <input> as an empty string, and
users can hand-edit URLs, so raw values are normalized here before they
reach the service layer.
"""


def blank_to_none(value: str | None) -> str | None:
    """``None`` for a missing or empty field, otherwise the value unchanged."""
    return value or None


def to_int_or_none(value: str | None) -> int | None:
    """The field as an int, or ``None`` if it is missing, empty or not a number.

    Lets a page ignore e.g. ``?year_from=abc`` instead of failing with a 422.
    Not ``str.isdigit()``: it accepts e.g. "²", which ``int()`` then rejects.
    """
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
