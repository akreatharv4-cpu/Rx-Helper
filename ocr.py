"""
Optimized OCR utilities for Rx-Helper v3.0
Enhanced for EasyOCR + BioBERT NER + Clinical Context Extraction
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
# This model is specifically trained to recognize Drugs, Chemicals, and Diseases
try:
    med_ner_pipeline = pipeline(
        "ner", 
        model="d4data/biomedical-ner-all", 
        aggregation_strategy="simple"
    )
    logger.info("✅ BioBERT Clinical NER loaded successfully.")
except Exception as e:
    logger.warning(f"⚠️ BioBERT load failed: {e}. Falling back to regex.")
    med_ner_pipeline = None

# ---------------- EASYOCR INITIALIZATION ----------------
reader = None

def get_reader():
    global reader
    if reader is None:
        import easyocr
        logger.info("🔄 Initializing EasyOCR Engine...")
        # gpu=True is recommended if you have an NVIDIA GPU
        reader = easyocr.Reader(['en'], gpu=False) 
    return reader

# ---------------- DATA LOADING (Abbreviations) ----------------
try:
    with open(BASE_DIR / "abbreviations.json", "r", encoding="utf-8") as f:
        ABBR = json.load(f)
except Exception:
    # Standard Clinical fallback if JSON is missing
    ABBR = {"tid": "three times a day", "bid": "twice a day", "qid": "four times a day", "od": "once daily"}

# ---------------- PREPROCESSING (Optimized for AI) ----------------

def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def preprocess_image(img: Image.Image) -> np.ndarray:
    """
    Optimized for EasyOCR: Focuses on contrast and sharpness
    rather than aggressive binary thresholding.
    """
    img_cv = _pil_to_cv2(img)
    
    # 1. Grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 2. Contrast Enhancement (CLAHE)
    # This helps read faint handwriting or prescriptions in low light
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    # 3. Bilateral Filter
    # Removes noise while keeping edges (text) sharp
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

    return denoised

# ---------------- OCR CLEANING ----------------

def clean_ocr_text(text: str) -> str:
    if not text: return ""

    # Fix common OCR character confusion
    replacements = {
        "|": "l", "§": "s", "€": "e", "ﬁ": "fi", "ﬂ": "fl",
        "0mg": "0 mg", "1mg": "1 mg", "lmg": "1 mg",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Remove non-ASCII noise but keep medical punctuation
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    # Normalize spacing
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# ---------------- ENTITY EXTRACTION ----------------

def extract_clean_drugs(text: str) -> List[str]:
    """
    Uses BioBERT to find medications. 
    Filters out common noise and non-drug clinical terms.
    """
    if not text or not med_ner_pipeline:
        return []

    # BioBERT NER Inference
    entities = med_ner_pipeline(text)
    
    drugs = []
    seen = set()
    
    # Clinical stop words that BERT sometimes confuses for drugs
    clinical_noise = {"patient", "doctor", "history", "diagnosis", "tablet", "capsule", "clinic"}

    for e in entities:
        label = str(e.get("entity_group", "")).lower()
        word = str(e.get("word", "")).strip().lower()

        # Target: Chemicals and Medications
        if any(tag in label for tag in ["chem", "drug", "med"]):
            # Clean BERT tokens (remove ## from sub-words)
            word = word.replace("##", "").strip(" ,.;:()[]{}")
            
            if word not in seen and len(word) > 2 and word not in clinical_noise:
                seen.add(word)
                drugs.append(word)

    return drugs

# ---------------- TOP-LEVEL OCR FUNCTIONS ----------------

def ocr_image_bytes(image_bytes: bytes) -> str:
    """Entry point for image files (JPEG, PNG)."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(img)

        # Execute OCR
        ocr_engine = get_reader()
        result = ocr_engine.readtext(processed, detail=0, paragraph=True)
        
        raw_text = " ".join(result)
        return clean_ocr_text(raw_text)
        
    except Exception as e:
        logger.error(f"OCR Pipeline failed: {e}")
        return ""

def ocr_pdf_bytes(pdf_bytes: bytes) -> str:
    """Entry point for PDF prescriptions."""
    try:
        from pdf2image import convert_from_bytes
        # Convert PDF pages to PIL images
        pages = convert_from_bytes(pdf_bytes, dpi=300)
        
        full_text = []
        ocr_engine = get_reader()
        
        for page in pages:
            processed = preprocess_image(page)
            result = ocr_engine.readtext(processed, detail=0, paragraph=True)
            full_text.append(" ".join(result))
            
        return clean_ocr_text("\n".join(full_text))
        
    except Exception as e:
        logger.error(f"PDF OCR Pipeline failed: {e}")
        return ""