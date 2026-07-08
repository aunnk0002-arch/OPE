"""
core/excel_exporter.py

Builds a fixed Excel workbook from parsed transaction rows.
"""

from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import ROW_NUMBERING_MODE


def build_workbook(transactions: list):
    """Return an openpyxl workbook for the supplied transactions."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Transactions"

    headers = ["Row", "Date", "Category", "Particular", "Amount", "Remarks"]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    for col_idx, header in enumerate(headers, start=1):
        cell = worksheet.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    row_numbers = _compute_row_numbers(transactions)
    for index, txn in enumerate(transactions):
        row_idx = index + 2
        worksheet.cell(row=row_idx, column=1, value=row_numbers[index])
        worksheet.cell(row=row_idx, column=2, value=txn.date or "")
        worksheet.cell(row=row_idx, column=3, value=txn.category or "")
        worksheet.cell(row=row_idx, column=4, value=txn.particular or "")
        worksheet.cell(row=row_idx, column=5, value=txn.amount if txn.amount is not None else "")
        worksheet.cell(row=row_idx, column=6, value=txn.remarks or "")

    for col_idx in range(1, len(headers) + 1):
        worksheet.column_dimensions[get_column_letter(col_idx)].width = 16

    worksheet.freeze_panes = "A2"
    return workbook


def _compute_row_numbers(transactions: List[Any]) -> List[int]:
    """Return the row-number sequence for the supplied transactions."""
    if ROW_NUMBERING_MODE == "continuous":
        return list(range(1, len(transactions) + 1))

    numbers = []
    counters: Dict[str, int] = {}
    for txn in transactions:
        category = txn.category or "Unknown"
        counters[category] = counters.get(category, 0) + 1
        numbers.append(counters[category])
    return numbers
