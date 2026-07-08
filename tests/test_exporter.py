import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.excel_exporter import build_workbook
from models.transaction import Transaction


def test_build_workbook_creates_fixed_sheet():
    workbook = build_workbook([Transaction(date="2026-01-01", amount=123.45, remarks="Paid")])

    ws = workbook["Transactions"]
    assert ws["A1"].value == "Row"
    assert ws["B2"].value == "2026-01-01"
    assert ws["E2"].value == 123.45
    assert ws["F2"].value == "Paid"
