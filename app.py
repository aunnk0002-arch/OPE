"""
app.py

This is the web page itself. Run it with:  streamlit run app.py

Flow:
  1. User uploads a folder (or individual files) of payment screenshots
  2. Each image goes through OCR -> template detection -> parsing
  3. Results are shown in an editable table -- fix mistakes, delete rows
     that shouldn't be there, then export
  4. User picks which fields to include and types their own column
     titles -- no hardcoded column names
  5. User downloads the final Excel file, built exactly to their spec
  6. "Start Over" clears everything for the next batch
"""

import io
import streamlit as st
from PIL import Image

from core.ocr_engine import extract_text
from core.template_detector import detect_and_parse
from core.excel_exporter import build_workbook
from models.transaction import Transaction

# Every field we can offer for export, with a sensible default title
# and default on/off state.
AVAILABLE_FIELDS = [
    {"field": "date", "default_title": "Date", "default_on": True},
    {"field": "category", "default_title": "Category", "default_on": True},
    {"field": "particular", "default_title": "Particular", "default_on": True},
    {"field": "amount", "default_title": "Amount", "default_on": True},
    {"field": "remarks", "default_title": "Remarks", "default_on": True},
    {"field": "transaction_id", "default_title": "Transaction ID", "default_on": False},
    {"field": "source_file", "default_title": "Source File", "default_on": False},
]

st.set_page_config(page_title="Pixel-Flow", layout="wide")

st.markdown("""
<style>
h1 { font-size: 2.1rem !important; margin-bottom: 0.2rem; }
div.stButton > button, div.stDownloadButton > button {
    background-color: #F97316 !important;
    color: white !important;
    border: none !important;
    padding: 0.5rem 1.3rem !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #EA580C !important;
}
</style>
""", unsafe_allow_html=True)

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# --- Header + Start Over button -----------------------------------------
header_col, reset_col = st.columns([5, 1])
with header_col:
    st.title("Pixel-Flow")
    st.caption("Turn payment screenshots into a formatted Excel file.")
with reset_col:
    st.write("")
    if st.button("Start Over"):
        st.session_state.pop("results", None)
        st.session_state["uploader_key"] += 1
        st.rerun()

# --- Upload ----------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload a folder of screenshots, or select individual files",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files="directory",
    key=f"uploader_{st.session_state['uploader_key']}",
)

if uploaded_files:
    if st.button("Process screenshots", type="primary"):
        results = []
        progress = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            try:
                image = Image.open(uploaded_file)
                raw_text = extract_text(image)
                txn = detect_and_parse(raw_text, uploaded_file.name)

                if txn is None:
                    txn = Transaction(
                        source_file=uploaded_file.name,
                        template_matched="UNRECOGNIZED",
                        raw_ocr_text=raw_text,
                        parse_warnings=["No matching app template found. Please fill in manually."],
                    )
            except Exception as e:
                txn = Transaction(
                    source_file=uploaded_file.name,
                    template_matched="ERROR",
                    parse_warnings=[f"Could not process this file: {e}"],
                )

            results.append(txn)
            progress.progress((i + 1) / len(uploaded_files), text=f"Processed {uploaded_file.name}")

        progress.empty()
        st.session_state["results"] = results

if "results" in st.session_state:
    results = st.session_state["results"]

    total = len(results)
    flagged = sum(1 for t in results if t.parse_warnings)
    clean = total - flagged
    st.info(f"**{total}** file(s) processed  |  Ready: **{clean}**  |  Flagged for review: **{flagged}**")

    st.subheader("Review extracted data")

    # Show ALL available fields in the review table (not just a fixed
    # subset), so the user can see everything we detected before
    # deciding what to export.
    rows = []
    for txn in results:
        rows.append({
            "Status": "Needs Review" if txn.parse_warnings else "OK",
            "Date": txn.date or "",
            "Category": txn.category or "",
            "Particular": txn.particular or "",
            "Amount": txn.amount if txn.amount is not None else None,
            "Remarks": txn.remarks or "",
            "Transaction ID": txn.transaction_id or "",
            "Source File": txn.source_file,
        })
    rows.sort(key=lambda r: r["Date"] if r["Date"] else "9999-99-99")

    edited_rows = st.data_editor(
        rows,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Status": st.column_config.TextColumn(disabled=True),
            "Amount": st.column_config.NumberColumn(format="%.2f"),
            "Transaction ID": st.column_config.TextColumn(disabled=True),
            "Source File": st.column_config.TextColumn(disabled=True),
        },
    )

    st.caption("Rows marked \"Needs Review\" above may have missing or uncertain fields -- edit any cell directly to fix them.")

    st.markdown(
        '<p style="color:#F97316; font-weight:600; margin-bottom:0.3rem; margin-top:1rem;">'
        'Customize column titles for your export:</p>',
        unsafe_allow_html=True,
    )
    export_columns = []
    for field_info in AVAILABLE_FIELDS:
        toggle_slot, title_slot = st.columns([1, 5])
        with toggle_slot:
            include = st.checkbox(
                field_info["default_title"],
                value=field_info["default_on"],
                key=f"include_{field_info['field']}",
            )
        with title_slot:
            title = st.text_input(
                "Column title",
                value=field_info["default_title"],
                key=f"title_{field_info['field']}",
                label_visibility="collapsed",
                disabled=not include,
            )
        if include:
            export_columns.append({"field": field_info["field"], "title": title or field_info["default_title"]})

    # --- Export ---
    st.subheader("Export")
    if not export_columns:
        st.warning("Select at least one column above to export.")
    elif st.button("Generate Excel file", type="primary"):
        final_transactions = []
        for row in edited_rows:
            amount = row.get("Amount")
            final_transactions.append(Transaction(
                date=row.get("Date") or None,
                category=row.get("Category") or None,
                particular=row.get("Particular") or None,
                amount=amount if amount not in (None, "") else None,
                remarks=row.get("Remarks") or None,
                transaction_id=row.get("Transaction ID") or None,
                source_file=row.get("Source File") or None,
            ))

        wb = build_workbook(final_transactions, export_columns)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        st.success(f"Excel file ready with {len(final_transactions)} transaction(s).")
        st.download_button(
            label="Download Excel file",
            data=buffer,
            file_name="transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("Upload screenshots above, then click 'Process screenshots' to get started.")