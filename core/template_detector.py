"""
core/template_detector.py

Tries each registered parser against a screenshot's OCR text and
returns the one that claims to recognize it.

TO ADD A NEW PAYMENT APP LATER:
  1. Create parsers/your_app.py following the same shape as
     parsers/kbz_pay.py (a class with `matches()` and `parse()`)
  2. Import it below and add it to PARSERS
That's the only change needed -- nothing else in the project needs
to know about the new app.
"""

from parsers.kbz_pay import KbzPayParser
from parsers.aya_pay import AyaPayParser

PARSERS = [
    KbzPayParser(),
    AyaPayParser(),
]


def detect_and_parse(raw_text: str, source_file: str):
    """
    Returns a Transaction if a parser recognized the screenshot,
    or None if no parser matched (meaning: unrecognized app/template,
    needs manual entry).
    """
    for parser in PARSERS:
        if parser.matches(raw_text):
            return parser.parse(raw_text, source_file)
    return None
