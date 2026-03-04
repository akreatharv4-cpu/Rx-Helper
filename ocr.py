import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

def ocr_image_bytes(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # simple preprocessing hook point (could add thresholding, etc.)
    text = pytesseract.image_to_string(img)
    return text.strip()

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=max_pages)
    out = []
    for page in pages:
        out.append(pytesseract.image_to_string(page))
    return "\n".join(out).strip()
