"""
parsers/base_parser.py

Shared utilities every app-specific parser can reuse (date extraction,
amount extraction, etc.) plus the common interface (BaseParser) every
parser must follow.

WHY A SHARED INTERFACE:
The rest of the app (template_detector.py, app.py) only ever calls
`parser.matches(text)` and `parser.parse(text, filename)`. It never
needs to know KBZ Pay's parser works differently from AYA Pay's parser
internally. This is what makes adding a new app later easy: write a
new file in this folder that follows the same shape, register it in
template_detector.py, done.
"""

import re
from datetime import datetime
from models.transaction import Transaction


class BaseParser:
    """Every parser (kbz_pay.py, aya_pay.py, ...) should inherit this
    and implement `matches()` and `parse()`."""

    name = "base"  # Override in subclasses, e.g. "KBZ Pay"

    def matches(self, raw_text: str) -> bool:
        """Return True if this parser recognizes the screenshot as
        belonging to its app, based on the OCR text."""
        raise NotImplementedError

    def parse(self, raw_text: str, source_file: str) -> Transaction:
        """Extract structured fields from OCR text into a Transaction."""
        raise NotImplementedError


# ---------------------------------------------------------------------
# Shared helpers — reused across multiple parsers
# ---------------------------------------------------------------------

def flatten(raw_text: str) -> str:
    """Collapse all whitespace/newlines into single spaces.
    Screenshots often break a name and its phone number across two
    OCR lines; flattening makes regex matching across that break easy."""
    return re.sub(r"\s+", " ", raw_text).strip()


def clean_amount(amount_str: str) -> float:
    """Turn '-900,000.00' or '45,000' into a plain float: -900000.0"""
    cleaned = amount_str.replace(",", "").strip()
    return float(cleaned)


def try_parse_date(date_str: str, formats: list) -> str:
    """Try a list of possible date formats against a raw date string.
    Returns 'YYYY-MM-DD' on success, or None if nothing matched."""
    date_str = date_str.strip()
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
