"""
Optimized OCR utilities for Rx-Helper
High accuracy + noise filtering + BioBERT Extraction
"""

from PIL import Image
import io
import logging
import cv2
import numpy as np
import re
import json
from typing import Optional, List
from pathlib import Path
from transformers import pipeline

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr")

BASE_DIR = Path(__file__).resolve().parent

# ---------------- BIOBERT NER SETUP ----------------
try:
    # Aggregation strategy "simple" merges sub-word tokens (##) automatically
    med_ner_pipeline = pipeline(
        "ner", 
        model="d4data/biomedical-ner-all", 
        aggregation_strategy="simple"
    )
    logger.info("✅ BioBERT model loaded successfully.")
except Exception as e:
    logger.warning(f"⚠️ Could not load BioBERT model: {e}")
    med_ner_pipeline = None

# ---------------- SAFE EASYOCR INIT ----------------
reader = None

def get_reader():
    global reader
    if reader is None:
        import easyocr
        logger.info("🔄 Loading EasyOCR model...")
        # gpu=False for compatibility, set True if you have a CUDA GPU
        reader = easyocr.Reader(['en'], gpu=False)
    return reader

# ---------------- DATA LOADING ----------------
try:
    with open(BASE_DIR / "abbreviations.json", "r", encoding="utf-8") as f:
        ABBR = json.load(f)
except Exception:
    ABBR = {}

# ---------------- OCR CLEANING & EXPANSION ----------------
def clean_ocr_errors(text: str) -> str:
    if not text: return ""

    replacements = {
        "|": "l", "§": "s", "€": "e", "—": "-", "–": "-",
        "0mg": "0 mg", "1mg": "1 mg", "lmg": "1 mg", "0. 5": "0.5",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Expand Abbreviations (e.g., bid -> twice a day)
    for k, v in ABBR.items():
        text = re.sub(rf"\b{re.escape(str(k))}\b", str(v), text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()

# ---------------- IMAGE PROCESSING ----------------
def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def preprocess_image(img: Image.Image, resize_min_width: int = 1200) -> np.ndarray:
    img_cv = _pil_to_cv2(img)
    h, w = img_cv.shape[:2]

    if w < resize_min_width and w > 0:
        scale = resize_min_width / float(w)
        img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=30) # Contrast boost
    
    # Sharpening Kernel
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel)

    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 3
    )

# ---------------- ENTITY EXTRACTION (NEW UPDATES) ----------------
def extract_clean_drugs(text: str) -> List[str]:
    """
    The heart of the analysis: Uses BioBERT to find drugs in the OCR text.
    """
    if not text or not med_ner_pipeline:
        return []

    entities = med_ner_pipeline(text)
    drugs = []
    seen = set()

    for e in entities:
        # Looking for chemical/drug/medication tags
        label = str(e.get("entity_group", "")).lower()
        word = str(e.get("word", "")).strip().lower()

        if label in ["chemical", "drug", "medication", "core_med"]:
            # Clean up punctuation attached by BERT
            word = word.replace("##", "").strip(" ,.;:()[]{}")
            
            if word not in seen and len(word) > 2:
                seen.add(word)
                drugs.append(word)

    return drugs

# ---------------- MAIN OCR FUNCTIONS ----------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    """Returns the raw cleaned text (needed for dose/frequency extraction)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        reader = get_reader()
        result = reader.readtext(processed, detail=0)
        raw_text = " ".join(result)

        return clean_ocr_errors(raw_text)
    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""

def ocr_pdf_bytes(pdf_bytes: bytes, dpi: int = 300, max_pages: Optional[int] = None) -> str:
    """Converts PDF to text via EasyOCR."""
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(pdf_bytes, dpi=dpi, last_page=max_pages)
        
        texts = []
        for page in pages:
            processed = preprocess_image(page)
            reader = get_reader()
            result = reader.readtext(processed, detail=0)
            texts.append(" ".join(result))
            
        return clean_ocr_errors("\n".join(texts))
    except Exception as e:
        logger.exception("PDF conversion error: %s", e)
        return ""