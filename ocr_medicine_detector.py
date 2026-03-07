import csv
import pytesseract
from PIL import Image

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load medicines from CSV
medicine_list = []

with open("medicine_dataset.csv", "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        medicine_list.append(row["medicine_name"].lower())

print("Total medicines loaded:", len(medicine_list))


# -----------------------------
# OCR TEXT EXTRACTION
# -----------------------------
def extract_text(image_file):

    img = Image.open(image_file)

    text = pytesseract.image_to_string(img)

    return text


# -----------------------------
# MEDICINE DETECTION
# -----------------------------
def detect_medicines(image_file):

    text = extract_text(image_file)

    detected = []

    for med in medicine_list:
        if med in text.lower():
            detected.append(med)

    detected = list(set(detected))   # remove duplicates

    return detected, text


# -----------------------------
# OPTIONAL TEST RUN
# -----------------------------
if __name__ == "__main__":

    medicines, text = detect_medicines("prescription.jpg")

    print("\nExtracted Text:\n")
    print(text)

    print("\nDetected Medicines:\n")
    print(medicines)
