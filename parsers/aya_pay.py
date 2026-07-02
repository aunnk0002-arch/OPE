"""
parsers/aya_pay.py

Handles AYA Pay screenshots. Two templates found in real samples:
  1. "E-Receipt / Transfer to Wallet" (light theme) -- labels and
     values sit on the same line, so this one is straightforward.
  2. "Payment Complete" (dark theme) -- icons in the layout confuse
     OCR's reading order, so the Sender/Receiver names can come out
     in a different order than they appear visually. We extract both
     names, make a best guess, and flag it with a warning so it's
     easy to double-check in the review table before export.
"""

import re
from parsers.base_parser import BaseParser, flatten, clean_amount, try_parse_date
from models.transaction import Transaction

# --- Light "E-Receipt" template ---------------------------------------
RECEIVER_NAME_PATTERN = re.compile(r"Receiver Name\s+(.+)")
SENDER_NAME_PATTERN = re.compile(r"Sender Name\s+(.+)")
DATE_AND_TIME_PATTERN = re.compile(
    r"Date and Time\s+(\d{1,2}\s+\w+\s+\d{4},?\s*\d{1,2}:\d{2}\s*[AP]M)"
)
NOTES_PATTERN = re.compile(r"Notes\s+(.+)")
AMOUNT_MMK_LABELED_PATTERN = re.compile(r"Amount\s+([\d,]+(?:\.\d{2})?)\s*MMK")

# --- Dark "Payment Complete" template ----------------------------------
GENERIC_AMOUNT_MMK_PATTERN = re.compile(r"([\d,]+\.\d{2})\s*MMK")
GENERIC_DATE_PATTERN = re.compile(
    r"(\d{1,2}\s+\w+\s+\d{4},?\s*\d{1,2}:\d{2}\s*[AP]M)"
)
DESCRIPTION_PATTERN = re.compile(r"Description\s+(.+?)(?:\s*\||$)")


class AyaPayParser(BaseParser):
    name = "AYA"

    def matches(self, raw_text: str) -> bool:
        text = raw_text.lower()
        return "aya" in text or "mmk" in text

    def parse(self, raw_text: str, source_file: str) -> Transaction:
        flat = flatten(raw_text)
        warnings = []

        txn = Transaction(
            category=self.name,
            source_file=source_file,
            raw_ocr_text=raw_text,
        )

        is_light_template = "receiver name" in flat.lower() or "sender name" in flat.lower()

        if is_light_template:
            txn.template_matched = "AYA Pay (E-Receipt)"
            self._parse_light_template(flat, txn, warnings)
        else:
            txn.template_matched = "AYA Pay (Payment Complete)"
            self._parse_dark_template(flat, txn, warnings)

        txn.parse_warnings = warnings
        return txn

    def _parse_light_template(self, flat, txn, warnings):
        receiver_match = RECEIVER_NAME_PATTERN.search(flat)
        if receiver_match:
            # Stop at the next known label word in case regex over-captures
            txn.particular = self._trim_to_next_label(receiver_match.group(1))
        else:
            warnings.append("receiver name not found")

        amount_match = AMOUNT_MMK_LABELED_PATTERN.search(flat)
        if amount_match:
            txn.amount = clean_amount(amount_match.group(1))
        else:
            warnings.append("amount not found")

        date_match = DATE_AND_TIME_PATTERN.search(flat)
        if date_match:
            txn.date = try_parse_date(date_match.group(1), ["%d %B %Y, %I:%M %p"])
        if not txn.date:
            warnings.append("date not found")

        notes_match = NOTES_PATTERN.search(flat)
        if notes_match:
            txn.remarks = self._trim_to_next_label(notes_match.group(1))
        else:
            warnings.append("notes/remarks not found")

    def _parse_dark_template(self, flat, txn, warnings):
        amount_match = GENERIC_AMOUNT_MMK_PATTERN.search(flat)
        if amount_match:
            txn.amount = clean_amount(amount_match.group(1))
        else:
            warnings.append("amount not found")

        date_match = GENERIC_DATE_PATTERN.search(flat)
        if date_match:
            txn.date = try_parse_date(date_match.group(1), ["%d %b %Y, %I:%M %p"])
        if not txn.date:
            warnings.append("date not found")

        # Names: find every ALL-CAPS-looking name (2+ words, all caps)
        # in the text. Order is unreliable in this template because of
        # icon interference, so we can't be 100% sure which is sender
        # vs receiver -- we take the LAST one found as a best guess for
        # "Particular" and flag it for manual review.
        name_candidates = re.findall(r"\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,4})\b", flat)
        if name_candidates:
            txn.particular = name_candidates[-1].strip()
            warnings.append(
                f"dark-theme layout: please verify counterparty "
                f"(candidates found: {', '.join(name_candidates)})"
            )
        else:
            warnings.append("counterparty name not found")

        desc_match = DESCRIPTION_PATTERN.search(flat)
        if desc_match:
            txn.remarks = desc_match.group(1).strip()
        else:
            warnings.append("notes/remarks not found")

    @staticmethod
    def _trim_to_next_label(value: str) -> str:
        """The light template's fields sit on one line each, but our
        flattened text has no line breaks, so a greedy regex could
        accidentally swallow the next label too. This trims off
        anything from the next known label onward."""
        known_labels = [
            "Amount", "Receiver Phone", "Receiver Name", "Sender Phone",
            "Sender Name", "Date and Time", "Notes", "Powered by",
        ]
        earliest_cut = len(value)
        for label in known_labels:
            pos = value.find(label)
            if pos != -1:
                earliest_cut = min(earliest_cut, pos)
        return value[:earliest_cut].strip()
