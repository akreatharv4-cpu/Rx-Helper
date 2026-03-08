import csv
import easyocr
from PIL import Image
import numpy as np

# ---------------- EASY OCR INITIALIZE ----------------

reader = easyocr.Reader(['en'], gpu=False)

# ---------------- LOAD MEDICINES ----------------

medicine_list = []

with open("medicine_dataset.csv", "r", encoding="utf-8") as file:
    reader_csv = csv.DictReader(file)

    for row in reader_csv:
        medicine_list.append(row["medicine_name"].lower())

print("Total medicines loaded:", len(medicine_list))


# ---------------- OCR TEXT EXTRACTION ----------------

def extract_text(image_file):

    img = Image.open(image_file).convert("RGB")

    img = np.array(img)

    results = reader.readtext(img)

    text = " ".join([r[1] for r in results])

    return text


# ---------------- MEDICINE DETECTION ----------------

def detect_medicines(image_file):

    text = extract_text(image_file)

    detected = []

    for med in medicine_list:

        if med in text.lower():
            detected.append(med)

    detected = list(set(detected))

    return detected, text


# ---------------- OPTIONAL TEST RUN ----------------

if __name__ == "__main__":

    medicines, text = detect_medicines("prescription.jpg")

    print("\nExtracted Text:\n")
    print(text)

    print("\nDetected Medicines:\n")
    print(medicines)
