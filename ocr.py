import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import cv2
import numpy as np

# ---------------- TESSERACT PATH (Render Linux) ----------------

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


# ---------------- OCR CONFIG ----------------

OCR_CONFIG = r"--oem 3 --psm 6"


# ---------------- IMAGE PREPROCESS ----------------

def preprocess_image(img: Image.Image):

    # convert PIL → numpy
    img = np.array(img)

    # ensure correct color format
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

    # remove noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # adaptive threshold (good for handwriting)
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    # sharpen
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpen = cv2.filter2D(thresh, -1, kernel)

    # resize for OCR accuracy
    resized = cv2.resize(
        sharpen,
        None,
        fx=1.5,
        fy=1.5,
        interpolation=cv2.INTER_CUBIC
    )

    return resized


# ---------------- IMAGE OCR ----------------

def ocr_image_bytes(image_bytes: bytes) -> str:

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except:
        return ""

    processed = preprocess_image(img)

    text = pytesseract.image_to_string(
        processed,
        config=OCR_CONFIG
    )

    return text.strip()


# ---------------- PDF OCR ----------------

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:

    try:
        pages = convert_from_bytes(
            pdf_bytes,
            dpi=300,
            first_page=1,
            last_page=max_pages
        )
    except:
        return ""

    out = []

    for page in pages:

        processed = preprocess_image(page)

        text = pytesseract.image_to_string(
            processed,
            config=OCR_CONFIG
        )

        out.append(text)

    return "\n".join(out).strip()
