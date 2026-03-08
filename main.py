from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pytesseract
from PIL import Image
import pandas as pd
import io
import cv2
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


app = FastAPI()


# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- TESSERACT PATH ----------------

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


# ---------------- LOAD DATASETS ----------------

try:
    interactions = pd.read_csv("drug_interactions.csv")

    interactions["drug1"] = interactions["drug1"].str.lower()
    interactions["drug2"] = interactions["drug2"].str.lower()

except:
    interactions = pd.DataFrame(columns=["drug1","drug2","severity","message"])


try:
    medicines = pd.read_csv("medicines.csv")

    medicine_list = medicines["medicine_name"].str.lower().tolist()

except:
    medicine_list = []


# ---------------- DRUG CLASSIFICATION ----------------

drug_classes = {

    "amoxicillin":"Antibiotic",
    "azithromycin":"Antibiotic",
    "ceftriaxone":"Antibiotic",
    "ciprofloxacin":"Antibiotic",
    "doxycycline":"Antibiotic",

    "paracetamol":"Analgesic",
    "ibuprofen":"NSAID",

    "metformin":"Antidiabetic",
    "insulin":"Antidiabetic",

    "atenolol":"Antihypertensive",

    "pantoprazole":"Antacid"
}


antibiotics = [
    "amoxicillin","azithromycin","ciprofloxacin",
    "ceftriaxone","doxycycline","levofloxacin"
]


injections = [
    "ceftriaxone","insulin","diclofenac injection",
    "heparin","vitamin b12 injection"
]


# ---------------- HOME ----------------

@app.get("/")
def home():
    return {"message": "Rx Helper API Running"}


# ---------------- PRESCRIPTION ANALYSIS ----------------

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):

    contents = await file.read()

    image = Image.open(io.BytesIO(contents))


    # resize large images
    image = image.resize((1500,1500))


    # OCR preprocessing
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(gray).lower()


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


    detected_medicines = list(set(detected_medicines))
    detected_antibiotics = list(set(detected_antibiotics))
    detected_injections = list(set(detected_injections))


    # ---------------- CLASSIFICATION ----------------

    classifications = {}

    for med in detected_medicines:

        classifications[med] = drug_classes.get(med,"Unknown")


    # ---------------- DRUG INTERACTIONS ----------------

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

                row = match.iloc[0]

                interaction_results.append({

                    "drug1": d1,
                    "drug2": d2,
                    "severity": row["severity"],
                    "message": row["message"]

                })


    # ---------------- POLYPHARMACY ----------------

    polypharmacy = len(detected_medicines) >= 5


    dashboard = {

        "total_medicines": len(detected_medicines),
        "antibiotic_count": len(detected_antibiotics),
        "injection_count": len(detected_injections),
        "polypharmacy": polypharmacy

    }


    return {

        "extracted_text": text,

        "medicines_detected": detected_medicines,

        "antibiotics_detected": detected_antibiotics,

        "injections_detected": detected_injections,

        "drug_classification": classifications,

        "drug_interactions": interaction_results,

        "dashboard": dashboard

    }


# ---------------- PDF REPORT ----------------

@app.post("/report")
def generate_report(data: dict):

    file_name = "clinical_report.pdf"

    c = canvas.Canvas(file_name, pagesize=letter)

    y = 750

    c.drawString(50, y, "Rx Helper Clinical Report")

    y -= 40

    medicines = data.get("medicines", [])
    interactions = data.get("interactions", [])


    c.drawString(50, y, "Medicines Detected:")
    y -= 20


    for m in medicines:

        c.drawString(60, y, m)

        y -= 20


    y -= 20

    c.drawString(50, y, "Drug Interactions:")
    y -= 20


    for i in interactions:

        text = f"{i['drug1']} + {i['drug2']} : {i['severity']} risk"

        c.drawString(60, y, text)

        y -= 20


    c.save()

    return FileResponse(file_name)
