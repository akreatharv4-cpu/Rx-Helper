import pytesseract
from PIL import Image
import io
import cv2
import numpy as np

def preprocess_image(img: Image.Image):
    img_np = np.array(img)
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    # Simple binary threshold for Tesseract
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        processed = preprocess_image(img)
        return pytesseract.image_to_string(processed)
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def ocr_pdf_bytes(pdf_bytes: bytes) -> str:
    from pdf2image import convert_from_bytes
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=2)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(preprocess_image(page)) + " "
        return text.strip()
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""
