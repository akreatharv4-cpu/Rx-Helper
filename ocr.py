"""
Advanced OCR utilities for Rx-Helper

Features:
- Image preprocessing
- PDF OCR
- OCR error correction
- Prescription shorthand normalization
"""

from PIL import Image
import io
import shutil
import logging
import pytesseract
import cv2
import numpy as np
import json
import re
from typing import Optional, List
from pathlib import Path

# ---------------- LOGGING ----------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr")

BASE_DIR = Path(__file__).resolve().parent

# ---------------- TESSERACT DETECTION ----------------

_tesseract_path = shutil.which("tesseract")

if _tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_path
    logger.info(f"Tesseract found at {_tesseract_path}")
else:
    logger.warning("Tesseract not found in PATH")

# Improved OCR config
DEFAULT_CONFIG = "--oem 3 --psm 6 -l eng"

# ---------------- LOAD ABBREVIATIONS ----------------

try:
    with open(BASE_DIR / "abbreviations.json", "r", encoding="utf-8") as f:
        ABBR = json.load(f)
except Exception as e:
    logger.warning(f"Could not load abbreviations.json: {e}")
    ABBR = {}

# ---------------- OCR ERROR CORRECTION ----------------

def clean_ocr_errors(text: str) -> str:
    """
    Fix common OCR mistakes without breaking numeric doses.
    """
    if not text:
        return ""

    replacements = {
        "|": "l",
        "§": "s",
        "€": "e",
        "—": "-",
        "–": "-",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Normalize repeated spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------- PRESCRIPTION NORMALIZATION ----------------

def normalize_prescription(text: str) -> str:
    """
    Normalize prescription prefixes.
    """
    if not text:
        return ""

    replacements = {
        r"\btab\b": "",
        r"\btablet\b": "",
        r"\bcap\b": "",
        r"\bcapsule\b": "",
        r"\binj\b": "",
        r"\binjection\b": "",
        r"\bsyp\b": "",
        r"\bsyrup\b": "",
        r"\bsusp\b": "",
        r"\bsuspension\b": "",
        r"\bdrop\b": "",
        r"\bdrops\b": "",
    }

    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------- EXPAND MEDICAL ABBREVIATIONS ----------------

def expand_abbreviations(text: str) -> str:
    if not text:
        return ""

    for k, v in ABBR.items():
        text = re.sub(rf"\b{re.escape(str(k))}\b", str(v), text, flags=re.IGNORECASE)

    return text


# ---------------- PIL → CV2 ----------------

def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    arr = np.array(img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


# ---------------- IMAGE PREPROCESSING ----------------

def preprocess_image(
    img: Image.Image,
    resize_min_width: int = 1000
) -> np.ndarray:
    img_cv = _pil_to_cv2(img)
    h, w = img_cv.shape[:2]

    if w < resize_min_width and w > 0:
        scale = resize_min_width / float(w)
        img_cv = cv2.resize(
            img_cv,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # noise reduction
    gray = cv2.medianBlur(gray, 3)

    # contrast improvement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        3
    )

    return thresh


# ---------------- OCR IMAGE ----------------

def ocr_image_bytes(
    image_bytes: bytes,
    lang: str = "eng",
    config: str = DEFAULT_CONFIG
) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        text = pytesseract.image_to_string(
            processed,
            lang=lang,
            config=config
        )

        text = clean_ocr_errors(text)
        text = expand_abbreviations(text)
        text = normalize_prescription(text)

        return text.strip()

    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""


# ---------------- OCR PDF ----------------

def ocr_pdf_bytes(
    pdf_bytes: bytes,
    dpi: int = 300,
    max_pages: Optional[int] = None,
    lang: str = "eng"
) -> str:
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        logger.exception("pdf2image missing: %s", e)
        return ""

    try:
        if max_pages:
            pages = convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                first_page=1,
                last_page=max_pages
            )
        else:
            pages = convert_from_bytes(pdf_bytes, dpi=dpi)

    except Exception as e:
        logger.exception("PDF conversion error: %s", e)
        return ""

    texts: List[str] = []

    for page in pages:
        try:
            processed = preprocess_image(page)

            page_text = pytesseract.image_to_string(
                processed,
                lang=lang
            )

            page_text = clean_ocr_errors(page_text)
            page_text = expand_abbreviations(page_text)
            page_text = normalize_prescription(page_text)

            page_text = page_text.strip()
            if page_text:
                texts.append(page_text)

        except Exception as e:
            logger.exception("Page OCR error: %s", e)

    return "\n\n".join(texts)


# ---------------- CLI TEST ----------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr.py <image-or-pdf>")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, "rb") as f:
        data = f.read()

    if path.endswith(".pdf"):
        print(ocr_pdf_bytes(data))
    else:
        print(ocr_image_bytes(data))
