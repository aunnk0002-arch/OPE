"""
models/transaction.py

Defines the common shape every parser must produce, no matter which
payment app the screenshot came from. This is the "contract" between
parsers and everything downstream (the review table, the Excel export).

If you add a new payment app later, its parser just needs to return
one of these objects — nothing else in the app needs to change.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Transaction:
    # Core fields — map directly to your office Excel columns
    date: Optional[str] = None          # Stored as "YYYY-MM-DD"
    category: Optional[str] = None      # e.g. "KPay", "AYA"
    particular: Optional[str] = None    # Counterparty name / description
    amount: Optional[float] = None      # Numeric only, no currency symbols
    remarks: Optional[str] = None       # From the screenshot's "Notes" field

    # Metadata — not shown in Excel, but useful for debugging /
    # catching mistakes before export
    source_file: Optional[str] = None   # Which uploaded file this came from
    template_matched: Optional[str] = None  # Which parser handled it
    raw_ocr_text: str = ""              # Full OCR output, for troubleshooting
    parse_warnings: list = field(default_factory=list)  # e.g. "amount not found"

    def is_complete(self) -> bool:
        """A transaction is 'complete enough' if the fields that matter
        for bookkeeping were actually found."""
        return all([self.date, self.category, self.amount is not None])
