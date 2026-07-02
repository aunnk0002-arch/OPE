"""
core/ocr_engine.py

Single responsibility: take an image, return raw text.

Why this is its own file:
If we ever need better accuracy (e.g. switch to Google Cloud Vision,
or add image preprocessing like contrast boosting), we only touch this
file. Nothing else in the project needs to know HOW text was extracted,
only that `extract_text()` gives it text back.
"""

import pytesseract
from PIL import Image


def extract_text(image: Image.Image) -> str:
    """
    Takes a PIL Image (an uploaded screenshot) and returns the raw
    text Tesseract can read from it.

    Note: we deliberately do NOT convert to grayscale here. Testing
    against real KBZ Pay / AYA Pay screenshots showed grayscale
    conversion did not improve results, since these are clean,
    digitally-rendered screenshots (not photos), so Tesseract already
    performs well on the original image.
    """
    raw_text = pytesseract.image_to_string(image)
    return raw_text
