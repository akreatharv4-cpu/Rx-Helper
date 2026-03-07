import csv
import pytesseract
from PIL import Image

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load medicines from CSV
medicine_list = []

with open("medicine_dataset.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        medicine_list.append(row["medicine_name"].lower())

print("Total medicines loaded:", len(medicine_list))


# OCR function
def extract_text(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text


# Detect medicines from OCR text
def detect_medicines(text):

    detected = []

    for med in medicine_list:
        if med in text.lower():
            detected.append(med)

    return detected


# Main analysis
def analyze_prescription(image_path):

    text = extract_text(image_path)

    medicines = detect_medicines(text)

    print("\nExtracted Text:\n")
    print(text)

    print("\nDetected Medicines:\n")
    print(medicines)


# Test run
analyze_prescription("prescription.jpg")
