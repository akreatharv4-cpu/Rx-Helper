"""
Advanced OCR utilities for Rx-Helper
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
    if not text: return ""
    replacements = {"|": "l", "§": "s", "€": "e", "—": "-", "–": "-"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip()

# ---------------- PRESCRIPTION NORMALIZATION ----------------
def normalize_prescription(text: str) -> str:
    if not text: return ""
    patterns = [r"\btab\b", r"\btablet\b", r"\bcap\b", r"\bcapsule\b", 
                r"\binj\b", r"\binjection\b", r"\bsyp\b", r"\bsyrup\b"]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()

def expand_abbreviations(text: str) -> str:
    if not text: return ""
    for k, v in ABBR.items():
        text = re.sub(rf"\b{re.escape(str(k))}\b", str(v), text, flags=re.IGNORECASE)
    return text

# ---------------- NEW: ADDED THIS TO FIX YOUR IMPORT ERROR ----------------
def extract_clean_drugs(text: str) -> str:
    """
    This is the function main.py was looking for.
    It runs the cleaning pipeline on a raw string.
    """
    if not text:
        return ""
    text = clean_ocr_errors(text)
    text = expand_abbreviations(text)
    text = normalize_prescription(text)
    return text.strip()

# ---------------- IMAGE PROCESSING ----------------
def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def preprocess_image(img: Image.Image, resize_min_width: int = 1000) -> np.ndarray:
    img_cv = _pil_to_cv2(img)
    h, w = img_cv.shape[:2]
    if w < resize_min_width and w > 0:
        scale = resize_min_width / float(w)
        img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)

# ---------------- MAIN OCR FUNCTIONS ----------------
def ocr_image_bytes(image_bytes: bytes, lang: str = "eng", config: str = DEFAULT_CONFIG) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)
        text = pytesseract.image_to_string(processed, lang=lang, config=config)
        return extract_clean_drugs(text)
    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""

def ocr_pdf_bytes(pdf_bytes: bytes, dpi: int = 300, max_pages: Optional[int] = None, lang: str = "eng") -> str:
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(pdf_bytes, dpi=dpi, last_page=max_pages) if max_pages else convert_from_bytes(pdf_bytes, dpi=dpi)
        texts = [extract_clean_drugs(pytesseract.image_to_string(preprocess_image(p), lang=lang)) for p in pages]
        return "\n\n".join(filter(None, texts))
    except Exception as e:
        logger.exception("PDF error: %s", e)
        return ""