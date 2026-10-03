"""
awesome_utils — a small, genuinely-working string/date helper library.

This is the "real" dependency: it does exactly what its README claims, so a
victim has every reason to install and keep it. The malicious behavior lives
entirely in the install hook (see setup.py), not here — which is precisely why
reading a package's runtime source is not enough to clear it.
"""
from datetime import datetime, timezone

__version__ = "1.3.7"
__all__ = ["shout", "slugify", "titlecase", "utcstamp"]


def shout(text: str) -> str:
    """Uppercase with an exclamation. `shout('hi') -> 'HI!'`"""
    return text.upper() + "!"


def slugify(text: str) -> str:
    """URL-safe slug. `slugify('Hello World') -> 'hello-world'`"""
    return "-".join(text.lower().split())


def titlecase(text: str) -> str:
    """Title-case each word. `titlecase('foo bar') -> 'Foo Bar'`"""
    return " ".join(w.capitalize() for w in text.split())


def utcstamp() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
