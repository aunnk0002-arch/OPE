# Payment Screenshot → Excel

Upload KBZ Pay / AYA Pay payment screenshots, review the extracted data,
and download a formatted Excel file matching your office's spreadsheet layout.

This guide assumes you have **never set this kind of project up before**.
Follow it top to bottom, in order.

---

## Part 1 — Install the required software

You need three things installed on your computer before touching the project:
**Python**, **Tesseract OCR**, and **VS Code**.

### 1. Install Python

1. Go to https://www.python.org/downloads/
2. Download the latest version (3.11 or higher)
3. Run the installer
   - **Windows:** on the first screen, tick the box **"Add Python to PATH"**
     before clicking Install. This step is easy to miss and causes problems
     later if skipped.
   - **Mac:** run the downloaded `.pkg` installer normally
4. Confirm it worked: open a terminal (see Part 2 below for how) and type:
   ```
   python --version
   ```
   You should see something like `Python 3.11.5`. If you get an error on
   Windows, restart your computer (PATH changes need a restart to take effect).

### 2. Install Tesseract OCR

This is the actual OCR engine that reads text from the screenshots. It's
separate from Python and must be installed on its own.

**Windows:**
1. Go to https://github.com/UB-Mannheim/tesseract/wiki
2. Download the Windows installer (`tesseract-ocr-w64-setup-...exe`)
3. Run it, keep the default install location
   (usually `C:\Program Files\Tesseract-OCR`)
4. **Important:** add this folder to your Windows PATH:
   - Search "Environment Variables" in the Windows Start menu
   - Click "Edit the system environment variables" → "Environment Variables"
   - Under "System variables," find `Path`, click Edit, click New
   - Paste in `C:\Program Files\Tesseract-OCR`
   - Click OK on all windows
5. Restart your computer

**Mac:**
1. Install Homebrew if you don't have it: https://brew.sh (follow the
   instructions on that page — one command pasted into Terminal)
2. Then run:
   ```
   brew install tesseract
   ```

**Confirm it worked** (any OS): open a terminal and type:
```
tesseract --version
```
You should see version info, not an error.

### 3. Install VS Code

1. Go to https://code.visualstudio.com/
2. Download and install for your OS (default settings are fine)
3. Open VS Code once installed
4. Install the **Python extension**:
   - Click the Extensions icon on the left sidebar (four squares icon)
   - Search "Python"
   - Install the one published by **Microsoft** (should be the first result)

---

## Part 2 — Open the project in VS Code

1. Download/save the project folder (`ocr-payment-excel`) somewhere on your
   computer, e.g. your Desktop or Documents folder
2. Open VS Code
3. Go to **File → Open Folder** (Mac: **File → Open...**)
4. Select the `ocr-payment-excel` folder and click Open
5. You should now see the file structure in the left sidebar (`app.py`,
   `core/`, `parsers/`, etc.)

**Open a terminal inside VS Code** (you'll use this a lot):
- Menu: **Terminal → New Terminal**
- A command-line panel opens at the bottom of the VS Code window
- All the commands below are typed into this panel, then press Enter

---

## Part 3 — Set up the Python environment

A "virtual environment" keeps this project's Python packages separate from
anything else on your computer. This avoids version conflicts later.

In the VS Code terminal, type each of these one at a time, pressing Enter
after each and waiting for it to finish:

**Create the virtual environment:**
```
python -m venv venv
```

**Activate it:**

Windows:
```
venv\Scripts\activate
```

Mac/Linux:
```
source venv/bin/activate
```

After activation, you should see `(venv)` appear at the start of your
terminal line. This means it worked, and every command from now on runs
inside this isolated environment.

> If VS Code shows a popup asking "Select a Python Interpreter" or similar,
> choose the one that mentions `venv`.

**Install the required packages:**
```
pip install -r requirements.txt
```
This will take a minute or two — it's downloading Streamlit, the OCR
library, Excel library, etc.

---

## Part 4 — Run the app

Still in the same VS Code terminal (with `(venv)` showing):

```
streamlit run app.py
```

This will:
- Print some URLs in the terminal
- Automatically open your web browser to the app (usually `http://localhost:8501`)

If it doesn't open automatically, copy the `http://localhost:8501` link
from the terminal into your browser manually.

**To stop the app:** click back in the terminal and press `Ctrl+C`.

**To run it again later:** you only need to repeat the "Activate it" step
from Part 3, then run `streamlit run app.py` again. You do NOT need to
reinstall packages every time — only the first time.

---

## Part 5 — Using the app

1. Click "Browse files" and select one or more screenshot images
   (hold Ctrl/Cmd to select multiple, or select-all in the file picker)
2. Click **"Process screenshots"**
3. Review the extracted table — double-click any cell to fix mistakes
4. Check the "⚠️ Items that may need manual review" section for anything
   flagged (e.g. AYA Pay's dark-theme screenshots need a quick manual check
   — see note below)
5. Click **"Generate Excel file"**, then **"Download Excel file"**

---

## What's supported right now (Phase 1)

| App | Templates recognized |
|---|---|
| KBZ Pay | E-Receipt (saved), Payment Successful (in-app) |
| AYA Pay | E-Receipt / Transfer to Wallet (light theme), Payment Complete (dark theme — flagged for manual review, see below) |

**Known limitation:** AYA Pay's dark "Payment Complete" template has icons
that confuse the OCR reading order, so the system can't always be 100%
sure which name is the sender vs receiver. It extracts both names and
makes a best guess, but flags the row so you can quickly double-check it
in the review table before exporting.

**Screenshots from unrecognized apps** (not yet built, e.g. Wave Pay) will
still appear in the table with blank fields, so you can fill them in by
hand instead of losing the upload entirely.

---

## Running the automated tests (optional, but recommended before making changes)

If you or a developer later modifies any parser, run this to make sure
nothing broke:
```
pytest tests/
```
This re-runs the real sample screenshots through the pipeline and checks
the results against known-correct values.

---

## Project structure (for reference)

```
ocr-payment-excel/
├── app.py                    # The web page itself (Streamlit)
├── config.py                 # Excel column layout — edit here if your office format changes
├── core/
│   ├── ocr_engine.py         # Wraps Tesseract OCR
│   ├── template_detector.py  # Figures out which app a screenshot is from
│   └── excel_exporter.py     # Builds the final .xlsx file
├── parsers/
│   ├── base_parser.py        # Shared code all parsers use
│   ├── kbz_pay.py            # KBZ Pay-specific field extraction
│   └── aya_pay.py            # AYA Pay-specific field extraction
├── models/
│   └── transaction.py        # The common data shape every parser produces
├── tests/
│   ├── test_parsers.py       # Automated tests
│   └── sample_screenshots/   # Real screenshots used as test cases
└── requirements.txt          # List of required Python packages
```

## Adding support for a new app later (e.g. Wave Pay)

1. Get 2-3 real sample screenshots of that app
2. Create `parsers/wave_pay.py`, following the same pattern as
   `parsers/kbz_pay.py`
3. Add it to the `PARSERS` list in `core/template_detector.py`
4. Add its samples to `tests/sample_screenshots/` and write a test in
   `tests/test_parsers.py`

(If you're not comfortable doing this yourself, just send the new sample
screenshots back to this conversation and it can be built for you the
same way KBZ Pay and AYA Pay were.)
