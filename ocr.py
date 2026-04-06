"""
OCR utilities for Rx-Helper
Upgraded: EasyOCR (AI-based) instead of Tesseract
"""

from PIL import Image
import io
import logging
import cv2
import numpy as np
import re
from typing import Optional
from pathlib import Path
import easyocr

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr")

BASE_DIR = Path(__file__).resolve().parent

# ---------------- EASYOCR INIT ----------------
reader = easyocr.Reader(['en'], gpu=False)


# ---------------- OCR CLEANING ----------------
def clean_ocr_errors(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "|": "l",
        "§": "s",
        "€": "e",
        "—": "-",
        "–": "-",
        "0mg": "0 mg",
        "1mg": "1 mg",
        "lmg": "1 mg",
        "0. 5": "0.5",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return re.sub(r"\s+", " ", text).strip()


# ---------------- IMAGE PROCESSING ----------------
def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def preprocess_image(img: Image.Image, resize_min_width: int = 1000) -> np.ndarray:
    img_cv = _pil_to_cv2(img)
    h, w = img_cv.shape[:2]

    # Resize
    if w < resize_min_width and w > 0:
        scale = resize_min_width / float(w)
        img_cv = cv2.resize(
            img_cv,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Improve contrast
    gray = cv2.convertScaleAbs(gray, alpha=2, beta=20)

    # Noise removal
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    return thresh


# ---------------- OCR IMAGE ----------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    AI OCR using EasyOCR
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        result = reader.readtext(processed)

        text = " ".join([r[1] for r in result])

        text = clean_ocr_errors(text)

        return text.strip()

    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""


# ---------------- OCR PDF ----------------
def ocr_pdf_bytes(pdf_bytes: bytes, dpi: int = 300, max_pages: Optional[int] = None) -> str:
    """
    AI OCR for PDF
    """
    try:
        from pdf2image import convert_from_bytes

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

    texts = []

    for page in pages:
        try:
            processed = preprocess_image(page)

            result = reader.readtext(processed)
            page_text = " ".join([r[1] for r in result])

            page_text = clean_ocr_errors(page_text)

            if page_text.strip():
                texts.append(page_text.strip())

        except Exception as e:
            logger.exception("Page OCR error: %s", e)

    return "\n\n".join(texts)


# ---------------- OPTIONAL FALLBACK ----------------
def extract_clean_drugs(text: str):
    """
    Temporary fallback to avoid import errors
    """
    return []