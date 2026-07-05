"""
app.py

This is the web page itself. Run it with:  streamlit run app.py

Flow:
  1. User uploads a folder (or individual files) of payment screenshots
  2. Each image goes through OCR -> template detection -> parsing
  3. Results are shown in an editable table -- fix mistakes, delete rows
     that shouldn't be there, then export
  4. User downloads the final Excel file
  5. "Start Over" clears everything for the next batch
"""

import io
import streamlit as st
from PIL import Image

from core.ocr_engine import extract_text
from core.template_detector import detect_and_parse
from core.excel_exporter import build_workbook
from models.transaction import Transaction

st.set_page_config(page_title="Pixel-Flow", layout="wide")

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

st.title("Pixel-Flow")
st.write("Turn payment screenshots into a formatted Excel file.")

header_col, reset_col = st.columns([8, 1])
with reset_col:
    if st.button("Start Over"):
        st.session_state.pop("results", None)
        st.session_state["uploader_key"] += 1
        st.rerun()

uploaded_files = st.file_uploader(
    "Upload a folder of screenshots, or select individual files",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files="directory",
    label_visibility="collapsed",
    key=f"uploader_{st.session_state['uploader_key']}",
)

if uploaded_files:
    if st.button("Process screenshots"):
        results = []
        progress = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            try:
                with Image.open(uploaded_file) as image:
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

    metric_cols = st.columns(3)
    with metric_cols[0]:
        st.metric("Processed", total)
    with metric_cols[1]:
        st.metric("Ready", clean)
    with metric_cols[2]:
        st.metric("Flagged", flagged)

    st.info(f"Processed: **{total}** files | Ready: **{clean}** | Flagged for review: **{flagged}**")

    st.subheader("Review extracted data")
    st.caption(
        "Double-click any cell to correct it. Rows with warnings are flagged below the table. "
        "You can also delete a row if a screenshot should not be included."
    )

    rows = []
    for txn in results:
        rows.append({
            "Status": "Needs Review" if txn.parse_warnings else "OK",
            "Date": txn.date or "",
            "Category": txn.category or "",
            "Particular": txn.particular or "",
            "Amount": txn.amount if txn.amount is not None else None,
            "Remarks": txn.remarks or "",
            "Source File": txn.source_file,
        })

    rows.sort(key=lambda row: row["Date"] or "9999-99-99")

    edited_rows = st.data_editor(
        rows,
        num_rows="dynamic",
        column_config={
            "Status": st.column_config.TextColumn(disabled=True),
            "Amount": st.column_config.NumberColumn(format="%.2f"),
            "Source File": st.column_config.TextColumn(disabled=True),
        },
        key=f"review_editor_{st.session_state['uploader_key']}",
    )

    rows = list(edited_rows)

    if flagged > 0:
        with st.expander(f"{flagged} item(s) that may need manual review", expanded=True):
            for txn in results:
                if txn.parse_warnings:
                    st.write(f"**{txn.source_file}**: " + "; ".join(txn.parse_warnings))

    st.subheader("Export")
    if st.button("Generate Excel file"):
        final_transactions = []
        for row in rows:
            final_transactions.append(Transaction(
                date=row.get("Date") or None,
                category=row.get("Category") or None,
                particular=row.get("Particular") or None,
                amount=row.get("Amount") if row.get("Amount") is not None else None,
                remarks=row.get("Remarks") or None,
            ))

        wb = build_workbook(final_transactions)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        st.success(f"Excel file ready with {len(final_transactions)} transaction(s).")
        st.download_button(
            label="Download Excel file",
            data=buffer,
            file_name="transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument/spreadsheetml.sheet",
        )
else:
    st.info("Upload screenshots above, then click 'Process screenshots' to get started.")
