"""
parsers/aya_pay.py

Handles AYA Pay screenshots. Templates found in real samples:
  1. "E-Receipt / Transfer to Wallet" (light theme) -- labels and
     values sit on the same line, straightforward to parse. This same
     pattern also covers the transaction "History" detail screen,
     which uses the same field labels.
  2. "Payment Complete" (dark theme) -- icons in the layout confuse
     OCR's reading order, so Sender/Receiver names can come out in a
     different order than they appear visually. We extract both names,
     make a best guess, and flag it for manual review.
  3. Utility / Top-up payments (e.g. "Top-up to MPT") -- these have NO
     person's name at all, just a phone number being topped up. Labels
     and values are grouped in separate blocks (all labels first, then
     all values in the same order), so this needs its own extraction
     logic rather than reusing the other two.
"""

import re
from parsers.base_parser import BaseParser, flatten, clean_amount, try_parse_date
from models.transaction import Transaction

# --- Light "E-Receipt" / History detail template ------------------------
RECEIVER_NAME_PATTERN = re.compile(r"Receiver Name\s+(.+)")
SENDER_NAME_PATTERN = re.compile(r"Sender Name\s+(.+)")
DATE_AND_TIME_LABELED_PATTERN = re.compile(
    r"Date and Time\s+(\d{1,2}\s+\w+\s+\d{4},?\s*\d{1,2}:\d{2}\s*[AP]M)"
)
NOTES_PATTERN = re.compile(r"Notes\s+(.+)")
AMOUNT_MMK_LABELED_PATTERN = re.compile(r"Amount\s+([\d,]+(?:\.\d{2})?)\s*MMK")

# --- Dark "Payment Complete" template ------------------------------------
GENERIC_AMOUNT_MMK_PATTERN = re.compile(r"([\d,]+\.\d{2})\s*MMK")
GENERIC_DATE_PATTERN = re.compile(
    r"(\d{1,2}\s+\w+\s+\d{4},?\s*\d{1,2}:\d{2}\s*[AP]M)"
)
DESCRIPTION_PATTERN = re.compile(r"Description\s+(.+?)(?:\s*\||$)")

# --- Utility / Top-up template -------------------------------------------
UTILITY_LABELS = [
    "Transaction Type", "Transaction Code", "Transaction Status",
    "Date and Time", "Phone Number", "Amount", "Total",
]
# Two possible date formats seen across samples: abbreviated month
# ("24 Apr 2026") and full month name ("1 August 2025")
DATE_FORMATS = ["%d %B %Y, %I:%M %p", "%d %b %Y, %I:%M %p"]


class AyaPayParser(BaseParser):
    name = "AYA"

    def matches(self, raw_text: str) -> bool:
        text = raw_text.lower()
        return "aya" in text or "mmk" in text

    def parse(self, raw_text: str, source_file: str) -> Transaction:
        flat = flatten(raw_text)
        flat_lower = flat.lower()
        warnings = []

        txn = Transaction(
            category=self.name,
            source_file=source_file,
            raw_ocr_text=raw_text,
        )

        is_light_template = "receiver name" in flat_lower or "sender name" in flat_lower
        is_utility_template = (
            not is_light_template
            and "transaction type" in flat_lower
            and "transaction code" in flat_lower
        )

        if is_light_template:
            txn.template_matched = "AYA Pay (E-Receipt / History)"
            self._parse_light_template(flat, txn, warnings)
        elif is_utility_template:
            txn.template_matched = "AYA Pay (Utility/Top-up)"
            self._parse_utility_template(flat, txn, warnings)
        else:
            txn.template_matched = "AYA Pay (Payment Complete)"
            self._parse_dark_template(flat, txn, warnings)

        txn.parse_warnings = warnings
        return txn

    def _parse_light_template(self, flat, txn, warnings):
        receiver_match = RECEIVER_NAME_PATTERN.search(flat)
        if receiver_match:
            txn.particular = self._trim_to_next_label(receiver_match.group(1))
        else:
            warnings.append("receiver name not found")

        amount_match = AMOUNT_MMK_LABELED_PATTERN.search(flat)
        if amount_match:
            txn.amount = clean_amount(amount_match.group(1))
        else:
            warnings.append("amount not found")

        date_match = DATE_AND_TIME_LABELED_PATTERN.search(flat)
        if date_match:
            txn.date = try_parse_date(date_match.group(1), DATE_FORMATS)
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
            txn.date = try_parse_date(date_match.group(1), DATE_FORMATS)
        if not txn.date:
            warnings.append("date not found")

        name_candidates = re.findall(r"\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,4})\b", flat)
        # "AYA PAY" / "AYA BANK" are branding text, not people -- filter out
        name_candidates = [n for n in name_candidates if "AYA" not in n]
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

    def _parse_utility_template(self, flat, txn, warnings):
        # Labels are all grouped together, followed by all values in the
        # same order -- values begin right after the last known label.
        last_label_end = 0
        for label in UTILITY_LABELS:
            idx = flat.find(label)
            if idx != -1:
                last_label_end = max(last_label_end, idx + len(label))
        values_text = flat[last_label_end:].strip()

        # First value = the transaction type/description, running up to
        # the first long digit sequence (the Transaction Code)
        type_match = re.match(r"^(.*?)(?=\d{6,})", values_text)
        if type_match and type_match.group(1).strip():
            txn.particular = type_match.group(1).strip()
        else:
            warnings.append("transaction type/description not found")

        date_match = GENERIC_DATE_PATTERN.search(flat)
        if date_match:
            txn.date = try_parse_date(date_match.group(1), DATE_FORMATS)
        if not txn.date:
            warnings.append("date not found")

        amount_match = re.search(r"([\d,]+(?:\.\d{2})?)\s*MMK", values_text)
        if amount_match:
            txn.amount = clean_amount(amount_match.group(1))
        else:
            warnings.append("amount not found")

        # This template has no "Notes" field -- genuinely blank, not a
        # parsing failure, so no warning added here.
        txn.remarks = None

    @staticmethod
    def _trim_to_next_label(value: str) -> str:
        known_labels = [
            "Amount", "Receiver Phone", "Receiver Name", "Sender Phone",
            "Sender Name", "Date and Time", "Notes", "Powered by", "Total",
        ]
        earliest_cut = len(value)
        for label in known_labels:
            pos = value.find(label)
            if pos != -1:
                earliest_cut = min(earliest_cut, pos)
        return value[:earliest_cut].strip()