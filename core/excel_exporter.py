"""
core/excel_exporter.py

Takes a list of Transaction objects and builds a .xlsx file matching
the office's spreadsheet format defined in config.py.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from config import EXCEL_COLUMNS, ROW_NUMBERING_MODE


def build_workbook(transactions: list) -> Workbook:
    """
    transactions: list of Transaction objects (see models/transaction.py)
    Returns an openpyxl Workbook ready to be saved or streamed to the browser.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"

    # --- Header row ---
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    for col_idx, col in enumerate(EXCEL_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col["header"])
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # --- Row numbering ---
    row_numbers = _compute_row_numbers(transactions)

    # --- Data rows ---
    for i, txn in enumerate(transactions):
        row_idx = i + 2  # row 1 is the header
        row_data = {
            "row_number": row_numbers[i],
            "date": txn.date or "",
            "category": txn.category or "",
            "particular": txn.particular or "",
            "amount": txn.amount if txn.amount is not None else "",
            "remarks": txn.remarks or "",
            "working": "",  # Left blank -- filled in manually by office staff
        }
        for col_idx, col in enumerate(EXCEL_COLUMNS, start=1):
            ws.cell(row=row_idx, column=col_idx, value=row_data[col["key"]])

    # --- Column widths (rough, readable defaults) ---
    widths = {"#": 6, "Date": 12, "Category": 12, "Particular": 28, "Amount": 14, "Remarks": 20, "Working": 12}
    for col_idx, col in enumerate(EXCEL_COLUMNS, start=1):
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = widths.get(col["header"], 15)

    ws.freeze_panes = "A2"
    return wb


def _compute_row_numbers(transactions: list) -> list:
    """Returns the '#' value for each transaction, according to
    config.ROW_NUMBERING_MODE."""
    if ROW_NUMBERING_MODE == "continuous":
        return list(range(1, len(transactions) + 1))

    # "per_category": restart numbering at 1 whenever the category changes
    numbers = []
    counters = {}
    for txn in transactions:
        cat = txn.category or "Unknown"
        counters[cat] = counters.get(cat, 0) + 1
        numbers.append(counters[cat])
    return numbers
