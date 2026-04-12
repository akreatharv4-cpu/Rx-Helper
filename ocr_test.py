import cv2
import numpy as np
import easyocr
from google.cloud import vision
import io
import os

# ---------- OCR INITIALIZATION ----------

# Initialize EasyOCR (Downloads models on first run)
reader = easyocr.Reader(['en'])

# For Google Vision: Set your credentials path here
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'your_key.json'

def preprocess_for_easyocr(image_path):
    """EasyOCR often works better with a slight contrast boost."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Increase contrast
    processed = cv2.convertScaleAbs(gray, alpha=1.2, beta=0)
    return processed

# ---------- ENGINE 1: EASYOCR (Local AI) ----------

def extract_text_easyocr(image_path):
    print("Running EasyOCR...")
    # EasyOCR can take the path directly or a processed image
    results = reader.readtext(image_path, detail=0) # detail=0 returns only text
    return " ".join(results)

# ---------- ENGINE 2: GOOGLE VISION (Cloud AI) ----------

def extract_text_vision(image_path):
    """
    State-of-the-art for handwriting. 
    Requires a Google Cloud Service Account Key.
    """
    print("Running Google Vision OCR...")
    try:
        client = vision.ImageAnnotatorClient()
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        # Using DOCUMENT_TEXT_DETECTION for dense medical text/handwriting
        response = client.document_text_detection(image=image)
        text = response.full_text_annotation.text

        if response.error.message:
            raise Exception(f"{response.error.message}")
        
        return text
    except Exception as e:
        return f"Vision OCR Error: {e} (Ensure API Key is set)"

# ---------- MEDICINE DETECTION (Upgraded) ----------

medicine_list = [
    "paracetamol", "amoxicillin", "pantoprazole", 
    "ibuprofen", "metformin", "azithromycin"
]

def detect_medicine(text):
    detected = []
    text_lower = text.lower()
    for med in medicine_list:
        if med in text_lower:
            detected.append(med.title())
    return list(set(detected))

# ---------- RUN TEST ON test.jpeg ----------

if __name__ == "__main__":
    # Pointing exactly to your requested file
    test_file = "test.jpeg"

    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found in current directory!")
    else:
        # 1. Try EasyOCR
        easy_text = extract_text_easyocr(test_file)
        print("\n--- EasyOCR Result ---")
        print(easy_text)
        print("Detected:", detect_medicine(easy_text))

        print("\n" + "="*30 + "\n")

        # 2. Try Google Vision (Uncomment if you have your JSON key set)
        # vision_text = extract_text_vision(test_file)
        # print("--- Google Vision Result ---")
        # print(vision_text)
        # print("Detected:", detect_medicine(vision_text))