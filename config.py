"""
config.py

Central place for settings that control HOW the output looks. If your
office changes its spreadsheet format later, this is the only file
that should need editing.
"""

# Column order and headers for the exported Excel file.
# This matches your office's existing spreadsheet format:
# #, Date, Category, Particular, Amount, Remarks, Working
EXCEL_COLUMNS = [
    {"key": "row_number", "header": "#"},
    {"key": "date", "header": "Date"},
    {"key": "category", "header": "Category"},
    {"key": "particular", "header": "Particular"},
    {"key": "amount", "header": "Amount"},
    {"key": "remarks", "header": "Remarks"},
    {"key": "working", "header": "Working"},  # Intentionally left blank on export
]

# Row-numbering behaviour: "per_category" restarts the "#" column at 1
# for each new Category group (matches the sample office sheet, where
# AYA rows are numbered 1-11, then KPay restarts at 1). Set to
# "continuous" for one running number across the whole sheet instead.
ROW_NUMBERING_MODE = "per_category"
