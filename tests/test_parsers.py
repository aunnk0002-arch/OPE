"""
tests/test_parsers.py

These tests run the real sample screenshots (in tests/sample_screenshots/)
through the full OCR + parsing pipeline and check the results against
known-correct values.

WHY THIS MATTERS LONG-TERM:
If you (or I, in a future session) change how a parser works -- say,
to improve accuracy or add a new field -- running `pytest` instantly
tells you whether that change broke something that used to work. This
is what "good structure for long-term use" concretely buys you.

Run with:  pytest tests/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from core.ocr_engine import extract_text
from core.template_detector import detect_and_parse

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "sample_screenshots")


def _run_pipeline(filename):
    image = Image.open(os.path.join(SAMPLES_DIR, filename))
    raw_text = extract_text(image)
    return detect_and_parse(raw_text, filename)


def test_kbz_pay_ereceipt_1():
    txn = _run_pipeline("kbz_pay_ereceipt_1.png")
    assert txn is not None
    assert txn.category == "KPay"
    assert txn.date == "2026-06-20"
    assert txn.particular == "DAW THAN AYE"
    assert txn.amount == 9000.0
    assert txn.remarks == "Payment"


def test_kbz_pay_ereceipt_2():
    txn = _run_pipeline("kbz_pay_ereceipt_2.jpg")
    assert txn is not None
    assert txn.category == "KPay"
    assert txn.date == "2025-09-01"
    assert txn.particular == "Nang Aye Yu Mon"
    assert txn.amount == 900000.0
    assert txn.remarks == "Family & Friends"


def test_kbz_pay_successful_1():
    txn = _run_pipeline("kbz_pay_successful_1.png")
    assert txn is not None
    assert txn.category == "KPay"
    assert txn.date == "2026-03-17"
    assert txn.particular == "U HLA SOE"
    assert txn.amount == 10000.0
    assert txn.remarks == "Payment"


def test_aya_pay_light_template():
    txn = _run_pipeline("aya_pay_light_1.png")
    assert txn is not None
    assert txn.category == "AYA"
    assert txn.date == "2026-06-05"
    assert txn.particular == "THU YA"
    assert txn.amount == 45000.0
    assert txn.remarks == "Payment"


def test_aya_pay_dark_template_extracts_amount_and_date():
    # The dark template's sender/receiver order isn't 100% reliable
    # (see parsers/aya_pay.py), so we only assert on the fields that
    # ARE reliable, and check that a review warning gets raised.
    txn = _run_pipeline("aya_pay_dark_1.png")
    assert txn is not None
    assert txn.category == "AYA"
    assert txn.date == "2026-04-24"
    assert txn.amount == 10000.0
    assert len(txn.parse_warnings) > 0


def test_unrecognized_screenshot_returns_none():
    # unknown_ks_icon_1.png is not from a supported app yet -- the
    # detector should say "I don't know this one" rather than guess.
    txn = _run_pipeline("unknown_ks_icon_1.png")
    assert txn is None
