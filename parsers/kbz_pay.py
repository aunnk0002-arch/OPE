"""
parsers/kbz_pay.py

Handles KBZ Pay screenshots. We found two visual templates in real
samples:
  1. "E-Receipt" (saved/shared receipt, blue card design)
  2. "Payment Successful" (in-app confirmation screen, status bar visible)

Both templates have the same underlying data in the same order. We
don't rely on field labels (some are too low-contrast for OCR to read
reliably) -- instead we match on value PATTERNS (date format, "Ks"
currency suffix, masked-phone-in-parentheses, etc), working line by
line rather than on one flattened blob of text. Line-by-line matching
avoids a bug we hit during testing: flattening the whole receipt into
one string let the word "Transfer" (from the "Transaction Type" line)
bleed into the start of the counterparty name on the next line.
"""

import re
from parsers.base_parser import BaseParser, flatten, clean_amount, try_parse_date
from models.transaction import Transaction

DATE_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}")
AMOUNT_KS_PATTERN = re.compile(r"(-?[\d,]+\.\d{2})\s*Ks")
# Matches a masked phone in parentheses, allowing OCR to sometimes
# insert a stray space inside the digits, e.g. "(******5 588)"
MASKED_PHONE_PATTERN = re.compile(r"\(\*+[\s\d]+\)")
NAME_WITH_PHONE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z\s\.]+?)\s*\(\*+[\s\d]+\)\s*$"
)
BOILERPLATE_MARKERS = ("thank you for using", "save e-receipt", "e-receipt only means")


class KbzPayParser(BaseParser):
    name = "KPay"  # Matches the category label used in the office Excel sheet

    def matches(self, raw_text: str) -> bool:
        text = raw_text.lower()
        has_kbz_branding = "kbz" in text
        has_ks_currency = bool(re.search(r"\bks\b", text))
        has_masked_phone = bool(MASKED_PHONE_PATTERN.search(raw_text))
        return has_kbz_branding or (has_ks_currency and has_masked_phone)

    def parse(self, raw_text: str, source_file: str) -> Transaction:
        warnings = []
        lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]

        txn = Transaction(
            category=self.name,
            source_file=source_file,
            template_matched="KBZ Pay",
            raw_ocr_text=raw_text,
        )

        # --- Date & time
        flat = flatten(raw_text)
        date_match = DATE_PATTERN.search(flat)
        if date_match:
            txn.date = try_parse_date(date_match.group(1), ["%d/%m/%Y"])
        else:
            warnings.append("date not found")

        # --- Amount + locate its line index (needed for notes extraction)
        amount_line_idx = None
        for idx, line in enumerate(lines):
            m = AMOUNT_KS_PATTERN.search(line)
            if m:
                txn.amount = abs(clean_amount(m.group(1)))
                amount_line_idx = idx
                break
        if txn.amount is None:
            warnings.append("amount not found")

        # --- Counterparty name (line-by-line, so "Transfer" on a
        # separate line never bleeds into the name)
        found_name = False
        for idx, line in enumerate(lines):
            same_line_match = NAME_WITH_PHONE_PATTERN.match(line)
            if same_line_match:
                txn.particular = same_line_match.group(1).strip()
                found_name = True
                break
            # Handle case where name and masked phone are on two lines
            if MASKED_PHONE_PATTERN.fullmatch(line) and idx > 0:
                candidate = lines[idx - 1]
                if candidate.lower() not in ("transfer",) and len(candidate) > 2:
                    txn.particular = candidate.strip()
                    found_name = True
                    break
        if not found_name:
            warnings.append("counterparty name not found")

        # --- Notes / Remarks: the line immediately after the amount
        # line, skipping anything that looks like boilerplate/logo noise
        if amount_line_idx is not None:
            notes = None
            for line in lines[amount_line_idx + 1:]:
                lowered = line.lower()
                if any(marker in lowered for marker in BOILERPLATE_MARKERS):
                    break
                notes = line
                break  # first non-boilerplate line only
            txn.remarks = notes
        if not txn.remarks:
            warnings.append("notes/remarks not found")

        txn.parse_warnings = warnings
        return txn
