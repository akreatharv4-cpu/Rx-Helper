# ocr_medicine_detector.py  (OPTIONAL helper)
import csv
from PIL import Image
from ocr import ocr_image_bytes, ocr_pdf_bytes

MEDICINES_CSV = "medicines.csv"

def load_medicine_list():
    meds = []
    try:
        with open(MEDICINES_CSV, newline='', encoding='utf-8') as fh:
            # Try to read first column or header 'name'
            reader = csv.DictReader(fh)
            if reader.fieldnames:
                key = reader.fieldnames[0]
                for row in reader:
                    val = row.get(key) or ""
                    if val:
                        meds.append(val.strip().lower())
            else:
                fh.seek(0)
                for line in fh:
                    meds.append(line.strip().lower())
    except FileNotFoundError:
        print(f"{MEDICINES_CSV} not found.")
    return meds


def detect_medicines_from_text(text, medicine_list):
    text_lower = text.lower()
    detected = []
    for m in medicine_list:
        if m and m in text_lower:
            detected.append(m)
    return detected


if __name__ == "__main__":
    meds = load_medicine_list()
    # example usage: run ocr on local image "prescription.jpg"
    try:
        with open("prescription.jpg", "rb") as f:
            b = f.read()
        text = ocr_image_bytes(b)
        print("Detected medicines:", detect_medicines_from_text(text, meds))
    except FileNotFoundError:
        print("No prescription.jpg for local test.")

  
