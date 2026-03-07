import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

medicine_list = [
    "paracetamol",
    "amoxicillin",
    "pantoprazole",
    "ibuprofen",
    "metformin",
    "azithromycin"
]

img = Image.open("prescription.jpg")
text = pytesseract.image_to_string(img)

print("\nExtracted Text:\n")
print(text)

detected = []

for med in medicine_list:
    if med.lower() in text.lower():
        detected.append(med)

print("\nDetected Medicines:")
print(detected)
