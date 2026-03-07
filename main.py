from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
import pandas as pd
import io

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tesseract path for Render
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Load datasets
try:
    interactions = pd.read_csv("drug_interactions.csv")
except:
    interactions = pd.DataFrame(columns=["drug1","drug2","severity","message"])

try:
    medicines = pd.read_csv("medicines.csv")
    medicine_list = medicines["medicine_name"].str.lower().tolist()
except:
    medicine_list = []

antibiotics = [
    "amoxicillin","azithromycin","ciprofloxacin",
    "ceftriaxone","doxycycline","levofloxacin"
]

injections = [
    "ceftriaxone","insulin","diclofenac injection",
    "heparin","vitamin b12 injection"
]


@app.get("/")
def home():
    return {"message": "Rx Helper API Running"}


@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # OCR extraction
    text = pytesseract.image_to_string(image).lower()

    words = text.split()

    detected_medicines = []
    detected_antibiotics = []
    detected_injections = []

    for word in words:
        if word in medicine_list:
            detected_medicines.append(word)

        if word in antibiotics:
            detected_antibiotics.append(word)

        if word in injections:
            detected_injections.append(word)

    # Drug interaction checking
    interaction_results = []

    for i in range(len(detected_medicines)):
        for j in range(i+1, len(detected_medicines)):

            d1 = detected_medicines[i]
            d2 = detected_medicines[j]

            match = interactions[
                ((interactions["drug1"] == d1) & (interactions["drug2"] == d2)) |
                ((interactions["drug1"] == d2) & (interactions["drug2"] == d1))
            ]

            if not match.empty:
                interaction_results.append({
                    "drug1": d1,
                    "drug2": d2,
                    "severity": match.iloc[0]["severity"],
                    "message": match.iloc[0]["message"]
                })

    return {
        "extracted_text": text,
        "medicines_detected": list(set(detected_medicines)),
        "antibiotics_detected": list(set(detected_antibiotics)),
        "injections_detected": list(set(detected_injections)),
        "drug_interactions": interaction_results
    }
