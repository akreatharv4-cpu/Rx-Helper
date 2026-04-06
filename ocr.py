"""
OCR utilities for Rx-Helper
ONLY handles text extraction (NO AI / NER here)
"""

from PIL import Image
import io
import shutil
import logging
import pytesseract
import cv2
import numpy as np
import re
from typing import Optional
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

# Better config for prescriptions
DEFAULT_CONFIG = "--oem 3 --psm 4 -l eng"


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

    # Resize for better OCR
    if w < resize_min_width and w > 0:
        scale = resize_min_width / float(w)
        img_cv = cv2.resize(
            img_cv,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Noise reduction
    gray = cv2.medianBlur(gray, 3)

    # Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Adaptive threshold (best for prescriptions)
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
    """
    Returns CLEAN TEXT (not drugs)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        text = pytesseract.image_to_string(
            processed,
            lang=lang,
            config=config
        )

        text = clean_ocr_errors(text)

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
    """
    Returns CLEAN TEXT from PDF
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

            page_text = pytesseract.image_to_string(
                processed,
                lang=lang
            )

            page_text = clean_ocr_errors(page_text)

            if page_text.strip():
                texts.append(page_text.strip())

        except Exception as e:
            logger.exception("Page OCR error: %s", e)

    return "\n\n".join(texts)