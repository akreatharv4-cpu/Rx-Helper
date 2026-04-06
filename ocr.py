"""
Optimized OCR utilities for Rx-Helper
High accuracy + noise filtering + prescription focus
"""

from PIL import Image
import io
import logging
import cv2
import numpy as np
import re
from typing import Optional
from pathlib import Path

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr")

BASE_DIR = Path(__file__).resolve().parent

# ---------------- SAFE EASYOCR INIT ----------------
reader = None

def get_reader():
    global reader
    if reader is None:
        import easyocr
        logger.info("🔄 Loading EasyOCR model...")
        reader = easyocr.Reader(['en'], gpu=False)
    return reader


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


def preprocess_image(img: Image.Image, resize_min_width: int = 1200) -> np.ndarray:
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

    # Contrast boost
    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=30)

    # Sharpen
    kernel = np.array([[0, -1, 0],
                       [-1, 5,-1],
                       [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        15,
        3
    )

    return thresh


# ---------------- TEXT FILTER ----------------
def filter_prescription_text(text: str) -> str:
    """
    Keep only medically relevant lines
    """
    lines = text.split("\n")

    filtered = []

    for line in lines:
        line = line.strip()

        # Skip empty or very short lines
        if len(line) < 3:
            continue

        # Keep lines that contain:
        # letters + numbers (like 500 mg)
        if re.search(r"[a-zA-Z]{3,}", line):
            filtered.append(line)

    return " ".join(filtered)


# ---------------- OCR IMAGE ----------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        reader = get_reader()
        result = reader.readtext(processed, detail=0)

        raw_text = "\n".join(result)

        text = clean_ocr_errors(raw_text)
        text = filter_prescription_text(text)

        return text.strip()

    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""


# ---------------- OCR PDF ----------------
def ocr_pdf_bytes(pdf_bytes: bytes, dpi: int = 300, max_pages: Optional[int] = None) -> str:
    try:
        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(
            pdf_bytes,
            dpi=dpi,
            first_page=1,
            last_page=max_pages if max_pages else None
        )

    except Exception as e:
        logger.exception("PDF conversion error: %s", e)
        return ""

    texts = []

    for page in pages:
        try:
            processed = preprocess_image(page)

            reader = get_reader()
            result = reader.readtext(processed, detail=0)

            raw_text = "\n".join(result)

            page_text = clean_ocr_errors(raw_text)
            page_text = filter_prescription_text(page_text)

            if page_text.strip():
                texts.append(page_text.strip())

        except Exception as e:
            logger.exception("Page OCR error: %s", e)

    return "\n\n".join(texts)


# ---------------- OPTIONAL ----------------
def extract_clean_drugs(text: str):
    """
    Not used anymore (kept for compatibility)
    """
    return []