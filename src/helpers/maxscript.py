"""Shared escaping helpers for building MAXScript strings."""


def safe_string(s: str) -> str:
    """Escape a Python string for embedding in a MAXScript double-quoted string literal.

    Handles backslash and double-quote — the two characters that break
    MAXScript "..." strings.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')


def safe_name(s: str) -> str:
    """Escape a Python string for use in a MAXScript $'...' name selector.

    Handles backslash, double-quote, and single-quote.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
