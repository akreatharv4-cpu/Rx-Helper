import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import cv2
import numpy as np


# ---------------- IMAGE PREPROCESS ----------------

def preprocess_image(img: Image.Image):

    img = np.array(img)

    # grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # remove noise
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    # adaptive threshold (better for medical handwriting)
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    # sharpen text
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpen = cv2.filter2D(thresh, -1, kernel)

    return sharpen


# ---------------- OCR CONFIG ----------------

OCR_CONFIG = r'--oem 3 --psm 6'


# ---------------- IMAGE OCR ----------------

def ocr_image_bytes(image_bytes: bytes) -> str:

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    processed = preprocess_image(img)

    text = pytesseract.image_to_string(
        processed,
        config=OCR_CONFIG
    )

    return text.strip()


# ---------------- PDF OCR ----------------

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:

    pages = convert_from_bytes(
        pdf_bytes,
        first_page=1,
        last_page=max_pages
    )

    out = []

    for page in pages:

        processed = preprocess_image(page)

        text = pytesseract.image_to_string(
            processed,
            config=OCR_CONFIG
        )

        out.append(text)

    return "\n".join(out).strip()
