"""
core/excel_exporter.py

Takes a list of Transaction objects and builds a .xlsx file using either
an imported custom template or the default export layout.
"""

from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import ROW_NUMBERING_MODE
from core.template_store import DEFAULT_TEMPLATE, load_template


def build_workbook(transactions: list, template: Optional[dict] = None) -> Workbook:
    """
    transactions: list of Transaction objects (see models/transaction.py)
    template: optional template dictionary containing custom column layout
    Returns an openpyxl Workbook ready to be saved or streamed to the browser.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"

    selected_template = template or load_template("Default") or DEFAULT_TEMPLATE
    columns = selected_template.get("columns", DEFAULT_TEMPLATE["columns"])

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col.get("header", ""))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    row_numbers = _compute_row_numbers(transactions)

    for i, txn in enumerate(transactions):
        row_idx = i + 2
        row_data = {
            "row_number": row_numbers[i],
            "date": txn.date or "",
            "category": txn.category or "",
            "particular": txn.particular or "",
            "amount": txn.amount if txn.amount is not None else "",
            "remarks": txn.remarks or "",
            "working": "",
        }
        for col_idx, col in enumerate(columns, start=1):
            key = col.get("key", "")
            value = row_data.get(key, "")
            ws.cell(row=row_idx, column=col_idx, value=value)

    for col_idx, _ in enumerate(columns, start=1):
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = 15

    ws.freeze_panes = "A2"
    return wb


def _compute_row_numbers(transactions: list) -> list:
    """Returns the '#' value for each transaction, according to config.ROW_NUMBERING_MODE."""
    if ROW_NUMBERING_MODE == "continuous":
        return list(range(1, len(transactions) + 1))

    numbers = []
    counters = {}
    for txn in transactions:
        cat = txn.category or "Unknown"
        counters[cat] = counters.get(cat, 0) + 1
        numbers.append(counters[cat])
    return numbers
