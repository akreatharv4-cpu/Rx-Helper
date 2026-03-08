import easyocr
from PIL import Image
from pdf2image import convert_from_bytes
import io
import cv2
import numpy as np

# ---------------- EASY OCR INITIALIZE ----------------

reader = easyocr.Reader(['en'], gpu=False)

# ---------------- IMAGE PREPROCESS ----------------

def preprocess_image(img: Image.Image):

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

    # adaptive threshold
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    # resize for better OCR accuracy
    resized = cv2.resize(
        thresh,
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

    results = reader.readtext(processed)

    text = " ".join([res[1] for res in results])

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

        results = reader.readtext(processed)

        text = " ".join([res[1] for res in results])

        out.append(text)

    return "\n".join(out).strip()
