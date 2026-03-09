import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io
import cv2
import numpy as np

# No manual path needed on Render/Linux
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def preprocess_image(img: Image.Image):
    img_np = np.array(img)
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    # Binary thresholding works best for Tesseract
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh

def ocr_image_bytes(image_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        processed = preprocess_image(img)
        # Convert processed numpy array back to PIL for Tesseract
        pil_img = Image.fromarray(processed)
        text = pytesseract.image_to_string(pil_img)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=max_pages)
        out = []
        for page in pages:
            processed = preprocess_image(page)
            pil_img = Image.fromarray(processed)
            text = pytesseract.image_to_string(pil_img)
            out.append(text)
        return "\n".join(out).strip()
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""
