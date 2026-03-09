# ocr.py
"""
Robust OCR helpers using pytesseract + pdf2image + OpenCV/Pillow.

Functions:
- preprocess_image(img: PIL.Image.Image) -> np.ndarray
- ocr_image_bytes(image_bytes: bytes, lang: str = "eng", config: str = DEFAULT_CONFIG) -> str
- ocr_pdf_bytes(pdf_bytes: bytes, dpi: int = 300, max_pages: int | None = None, lang: str = "eng") -> str
"""

from PIL import Image
import io
import shutil
import logging
import pytesseract
import cv2
import numpy as np
from typing import Optional, List

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr")

# Try to locate the tesseract binary automatically (works on Render/Docker/Linux/Windows)
_tesseract_path = shutil.which("tesseract")
if _tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_path
    logger.info(f"Using tesseract binary at: {_tesseract_path}")
else:
    logger.warning("Tesseract binary not found in PATH. Make sure tesseract is installed on the host.")

# sensible default config: oem 3 (default + LSTM), psm 6 (assume a block of text)
DEFAULT_CONFIG = "--oem 3 --psm 6"

def _pil_to_cv2(img: Image.Image) -> np.ndarray:
    """
    Convert PIL Image (RGB) to OpenCV BGR np.ndarray.
    """
    img = img.convert("RGB")
    arr = np.array(img)  # RGB
    # Convert RGB to BGR for OpenCV
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def preprocess_image(img: Image.Image,
                     resize_min_width: int = 1000,
                     denoise: bool = True,
                     sharpen: bool = True) -> np.ndarray:
    """
    Preprocess a PIL Image for better OCR results.

    Steps:
    - convert to BGR np.ndarray
    - optionally resize up if small (keeps readability)
    - convert to grayscale
    - denoise (median or bilateral)
    - contrast enhancement via CLAHE
    - adaptive thresholding or OTSU depending on image brightness
    - optional morphological opening to remove small noise
    - optional unsharp mask (sharpen)
    Returns: single-channel (grayscale) numpy array suitable for pytesseract.
    """
    try:
        img_cv = _pil_to_cv2(img)
    except Exception as e:
        logger.exception("Error converting PIL to OpenCV array: %s", e)
        raise

    h, w = img_cv.shape[:2]
    # Upscale if too small (helps OCR)
    if w < resize_min_width:
        scale = resize_min_width / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_cv = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("Resized image from (%d,%d) to (%d,%d)", w, h, new_w, new_h)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Denoise
    if denoise:
        # median blur is good for salt-and-pepper; bilateral preserves edges
        gray = cv2.medianBlur(gray, 3)
        gray = cv2.bilateralFilter(gray, d=5, sigmaColor=75, sigmaSpace=75)

    # Contrast limited adaptive histogram equalization (CLAHE)
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    except Exception:
        pass

    # Determine thresholding method based on image mean brightness
    mean_brightness = np.mean(gray)
    if mean_brightness > 200 or mean_brightness < 50:
        # very bright or very dark -> OTSU
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        # use adaptive threshold for variable lighting
        thresh = cv2.adaptiveThreshold(gray, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 15, 3)

    # Morphological opening to remove small specks
    kernel = np.ones((1, 1), np.uint8)
    try:
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    except Exception:
        pass

    # Optional sharpening (unsharp mask)
    if sharpen:
        try:
            gaussian = cv2.GaussianBlur(thresh, (0, 0), sigmaX=3)
            sharpened = cv2.addWeighted(thresh, 1.5, gaussian, -0.5, 0)
            thresh = sharpened
        except Exception:
            pass

    return thresh


def ocr_image_bytes(image_bytes: bytes,
                    lang: str = "eng",
                    config: str = DEFAULT_CONFIG) -> str:
    """
    Run OCR on an image provided as bytes. Returns extracted text.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.exception("Failed to open image bytes: %s", e)
        return ""

    try:
        processed = preprocess_image(img)
        # pytesseract accepts numpy arrays (single-channel or 3-channel)
        text = pytesseract.image_to_string(processed, lang=lang, config=config)
        return text.strip()
    except Exception as e:
        logger.exception("OCR Error: %s", e)
        return ""


def ocr_pdf_bytes(pdf_bytes: bytes,
                  dpi: int = 300,
                  max_pages: Optional[int] = None,
                  lang: str = "eng",
                  config: str = DEFAULT_CONFIG) -> str:
    """
    Convert PDF bytes to images and run OCR on each page.
    - dpi: resolution for conversion (300 recommended)
    - max_pages: if set, limit to first `max_pages` pages (None = all)
    Returns concatenated text.
    NOTE: requires pdf2image and poppler-utils installed on the host.
    """
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        logger.exception("pdf2image is required for PDF OCR: %s", e)
        return ""

    try:
        # If max_pages is set, pass it; else convert all pages
        if max_pages is not None:
            pages = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=1, last_page=max_pages)
        else:
            pages = convert_from_bytes(pdf_bytes, dpi=dpi)
    except Exception as e:
        logger.exception("Error converting PDF to images: %s", e)
        return ""

    texts: List[str] = []
    for idx, page in enumerate(pages, start=1):
        try:
            processed = preprocess_image(page)
            page_text = pytesseract.image_to_string(processed, lang=lang, config=config)
            texts.append(page_text.strip())
            logger.debug("OCR page %d length=%d", idx, len(page_text))
        except Exception as e:
            logger.exception("OCR failed for page %d: %s", idx, e)
            continue

    return "\n\n".join(t for t in texts if t)


# Small CLI test helper
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr.py <image-or-pdf-path>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "rb") as f:
            b = f.read()
        if path.lower().endswith(".pdf"):
            out = ocr_pdf_bytes(b, dpi=300, max_pages=5)
        else:
            out = ocr_image_bytes(b)
        print("------ OCR OUTPUT ------")
        print(out or "(no text)")
    except Exception as exc:
        logger.exception("Test failed: %s", exc)
        sys.exit(2)
