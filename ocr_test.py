import pytesseract
from PIL import Image
import cv2
import numpy as np

# ---------- IMAGE PREPROCESSING ----------

def preprocess_image(image_path):

    img = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove noise
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return thresh


# ---------- OCR FUNCTION ----------

def extract_text(image_path):

    processed = preprocess_image(image_path)

    # OCR configuration
    config = "--oem 3 --psm 6"

    text = pytesseract.image_to_string(processed, config=config)

    return text


# ---------- MEDICINE DETECTION ----------

medicine_list = [
    "paracetamol",
    "amoxicillin",
    "pantoprazole",
    "ibuprofen",
    "metformin",
    "azithromycin"
]

def detect_medicine(text):

    detected = []

    for med in medicine_list:
        if med.lower() in text.lower():
            detected.append(med)

    return detected


# ---------- RUN TEST ----------

if __name__ == "__main__":

    image_path = "prescription.jpg"

    text = extract_text(image_path)

    print("\nExtracted Text:\n")
    print(text)

    detected = detect_medicine(text)

    print("\nDetected Medicines:\n")
    print(detected)
