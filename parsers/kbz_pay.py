"""
parsers/kbz_pay.py

Handles KBZ Pay screenshots. Real samples have shown FOUR layout
variants so far:
  1. "E-Receipt" (saved/shared receipt, blue card design)
  2. "Payment Successful" (in-app confirmation screen, status bar visible)
  3. "Details" (transaction history detail view -- opened by tapping a
     past transaction; field labels ARE usually readable here)
  4. Merchant/bill payments (e.g. "Customer Buy Goods", "OnlinePayment
     MINIAPP") -- these have NO masked-phone-in-parentheses pattern
     (since there's no person, just a merchant code + name), and often
     include extra fields like "Service Fee" and "Total Amount"

All variants share the same underlying field order, so one parser
handles all of them. We don't rely purely on field labels (some are
too low-contrast for OCR), so we combine label-matching (when labels
ARE readable) with positional pattern-matching as a fallback.
"""

import re
from parsers.base_parser import BaseParser, flatten, clean_amount, try_parse_date
from models.transaction import Transaction

DATE_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}:\d{2}")
AMOUNT_KS_PATTERN = re.compile(r"(-?[\d,]+\.\d{2})\s*Ks")
MASKED_PHONE_PATTERN = re.compile(r"\(\*+[\s\d]+\)")
NAME_WITH_PHONE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z\s\.]+?)\s*\(\*+[\s\d]+\)\s*$"
)
TRANSFER_TO_LABEL_PATTERN = re.compile(r"^Transfer To\s*(.*)$", re.IGNORECASE)
# Transaction type values that carry no counterparty info by themselves
KNOWN_TYPE_ONLY_LINES = {
    "transfer", "onlinepayment miniapp", "customer buy goods",
    "cash in", "cash out", "top up",
}
# KBZ Pay transaction numbers observed so far all start with "0100"
# and run ~18-20 digits total -- a strong signal even when no other
# branding text is readable (e.g. the "Details" history screen).
KBZ_TXN_NO_PATTERN = re.compile(r"\b0100\d{14,18}\b")
BOILERPLATE_MARKERS = ("thank you for using", "save e-receipt", "e-receipt only means")


class KbzPayParser(BaseParser):
    name = "KPay"  # Matches the category label used in the office Excel sheet

    def matches(self, raw_text: str) -> bool:
        text = raw_text.lower()
        has_kbz_branding = "kbz" in text
        has_ks_currency = bool(re.search(r"\bks\b", text))
        has_masked_phone = bool(MASKED_PHONE_PATTERN.search(raw_text))
        has_kbz_txn_no = bool(KBZ_TXN_NO_PATTERN.search(raw_text))
        has_transaction_labels = ("transaction time" in text) or ("transaction no" in text)
        return (
            has_kbz_branding
            or (has_ks_currency and has_masked_phone)
            or (has_ks_currency and has_kbz_txn_no)
            or (has_ks_currency and has_transaction_labels)
        )

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

        # --- Amount + locate its line index (needed for name/notes extraction)
        amount_line_idx = None
        for idx, line in enumerate(lines):
            m = AMOUNT_KS_PATTERN.search(line)
            if m:
                txn.amount = abs(clean_amount(m.group(1)))
                amount_line_idx = idx
                break
        if txn.amount is None:
            warnings.append("amount not found")

        # --- Counterparty / Particular
        particular, found = self._extract_particular(lines, amount_line_idx)
        txn.particular = particular
        if not found and particular is None:
            warnings.append("counterparty name not found")

        # --- Notes / Remarks
        txn.remarks = self._extract_notes(lines, amount_line_idx)
        if not txn.remarks:
            # Not necessarily an error -- many merchant receipts genuinely
            # have no notes -- but flagged so it's easy to double check.
            warnings.append("no notes/remarks detected (may be genuinely blank)")

        txn.parse_warnings = warnings
        return txn

    @staticmethod
    def _extract_particular(lines, amount_line_idx):
        """Returns (value, was_found_via_label)."""
        # Strategy 1: explicit "Transfer To" label (readable in some
        # templates, e.g. the "Details" history screen)
        for idx, line in enumerate(lines):
            m = TRANSFER_TO_LABEL_PATTERN.match(line)
            if m:
                value_parts = [m.group(1).strip()] if m.group(1).strip() else []
                j = idx + 1
                while amount_line_idx is not None and j <= amount_line_idx:
                    nxt = lines[j]
                    if nxt.lower().startswith("amount") or AMOUNT_KS_PATTERN.search(nxt):
                        break
                    value_parts.append(nxt.strip())
                    j += 1
                value = " ".join(p for p in value_parts if p).strip()
                if value:
                    return value, True
                break  # label found but empty -- fall through to positional

        # Strategy 2: positional fallback -- the counterparty normally
        # sits on the line immediately before the amount+Ks line
        if amount_line_idx is not None and amount_line_idx > 0:
            idx = amount_line_idx - 1
            candidate = lines[idx].strip()

            # If that line is just a masked-phone fragment on its own
            # (name and phone were split across two OCR lines), the
            # real name is one line further up
            if candidate.startswith("(") and idx > 0:
                idx -= 1
                candidate = lines[idx].strip()

            if candidate.lower() in KNOWN_TYPE_ONLY_LINES:
                return None, False

            # Strip a trailing masked-phone parenthetical if the name
            # and phone were on the same line, e.g. "DAW THAN AYE (******7733)"
            paren_idx = candidate.find("(")
            if paren_idx > 2:
                candidate = candidate[:paren_idx].strip()

            if candidate:
                return candidate, False

        return None, False

    @staticmethod
    def _extract_notes(lines, amount_line_idx):
        if amount_line_idx is None:
            return None
        idx = amount_line_idx + 1
        while idx < len(lines):
            line = lines[idx]
            lowered = line.lower()
            if any(marker in lowered for marker in BOILERPLATE_MARKERS):
                break
            if AMOUNT_KS_PATTERN.search(line):
                # An extra amount-like field (Service Fee / Total Amount
                # on merchant receipts) -- not real notes, skip it
                idx += 1
                continue
            if lowered == "notes":
                # Just the "Notes" label itself with no value captured
                # on this line -- check the next line for the real value
                idx += 1
                continue
            return line
        return None