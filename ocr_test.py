import easyocr
from PIL import Image
import numpy as np

# ---------------- EASY OCR INITIALIZE ----------------

reader = easyocr.Reader(['en'], gpu=False)

medicine_list = [
    "paracetamol",
    "amoxicillin",
    "pantoprazole",
    "ibuprofen",
    "metformin",
    "azithromycin"
]

# ---------------- LOAD IMAGE ----------------

img = Image.open("prescription.jpg").convert("RGB")

img = np.array(img)

# ---------------- OCR TEXT EXTRACTION ----------------

results = reader.readtext(img)

text = " ".join([r[1] for r in results])

print("\nExtracted Text:\n")
print(text)

# ---------------- MEDICINE DETECTION ----------------

detected = []

for med in medicine_list:
    if med.lower() in text.lower():
        detected.append(med)

print("\nDetected Medicines:")
print(detected)
