"""
app.py

This is the web page itself. Run it with:  streamlit run app.py

Flow:
  1. User uploads one or more payment screenshots
  2. Each image goes through OCR -> template detection -> parsing
  3. Results are shown in an editable table so mistakes can be fixed
     by hand before export
  4. User downloads the final Excel file
"""

import io
import dataclasses
import pandas as pd
import streamlit as st
from PIL import Image

from core.ocr_engine import extract_text
from core.template_detector import detect_and_parse
from core.excel_exporter import build_workbook
from models.transaction import Transaction

st.set_page_config(page_title="Payment Screenshot to Excel", layout="wide")
st.title("📄 Payment Screenshot → Excel")
st.caption("Upload KBZ Pay / AYA Pay screenshots and get back a formatted Excel file.")

uploaded_files = st.file_uploader(
    "Upload screenshots (you can select multiple files at once)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

st.markdown(
    "**Tip:** most browsers let you select an entire folder's worth of images "
    "at once in the file picker dialog (select all, or drag-and-drop the folder's "
    "contents). This uploader accepts as many images as you select in one go."
)

if uploaded_files:
    if st.button("Process screenshots", type="primary"):
        results = []
        progress = st.progress(0, text="Processing...")

        for i, uploaded_file in enumerate(uploaded_files):
            image = Image.open(uploaded_file)
            raw_text = extract_text(image)
            txn = detect_and_parse(raw_text, uploaded_file.name)

            if txn is None:
                # No parser recognized this screenshot -- still show it
                # in the table so the user can fill fields in by hand
                # instead of losing the upload entirely.
                txn = Transaction(
                    source_file=uploaded_file.name,
                    template_matched="UNRECOGNIZED",
                    raw_ocr_text=raw_text,
                    parse_warnings=["No matching app template found. Please fill in manually."],
                )

            results.append(txn)
            progress.progress((i + 1) / len(uploaded_files), text=f"Processed {uploaded_file.name}")

        progress.empty()
        st.session_state["results"] = results

if "results" in st.session_state:
    results = st.session_state["results"]

    st.subheader("Review extracted data")
    st.caption("Double-click any cell to correct it before exporting. Rows with warnings are flagged below the table.")

    # Build an editable dataframe from the parsed transactions
    rows = []
    for txn in results:
        rows.append({
            "Date": txn.date or "",
            "Category": txn.category or "",
            "Particular": txn.particular or "",
            "Amount": txn.amount if txn.amount is not None else None,
            "Remarks": txn.remarks or "",
            "Source File": txn.source_file,
        })
    df = pd.DataFrame(rows)
    # Sort by date so the review table is always in chronological order,
    # regardless of the order files were uploaded/selected in. Rows with
    # no detected date (blank string) are pushed to the bottom rather
    # than the top.
    df["_sort_key"] = df["Date"].replace("", "9999-99-99")
    df = df.sort_values("_sort_key").drop(columns="_sort_key").reset_index(drop=True)

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Amount": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    # Show warnings for anything that needs a second look
    warnings_present = any(txn.parse_warnings for txn in results)
    if warnings_present:
        with st.expander("⚠️ Items that may need manual review", expanded=True):
            for txn in results:
                if txn.parse_warnings:
                    st.write(f"**{txn.source_file}**: " + "; ".join(txn.parse_warnings))

    # --- Export ---
    st.subheader("Export")
    if st.button("Generate Excel file", type="primary"):
        # Rebuild Transaction objects from the (possibly hand-edited) table
        final_transactions = []
        for _, row in edited_df.iterrows():
            final_transactions.append(Transaction(
                date=row["Date"] or None,
                category=row["Category"] or None,
                particular=row["Particular"] or None,
                amount=row["Amount"] if pd.notna(row["Amount"]) else None,
                remarks=row["Remarks"] or None,
            ))

        wb = build_workbook(final_transactions)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Download Excel file",
            data=buffer,
            file_name="transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("Upload screenshots above, then click 'Process screenshots' to get started.")