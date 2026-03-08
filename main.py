from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import pytesseract
from PIL import Image
import pandas as pd
import io
import cv2
import numpy as np
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rapidfuzz import process

app = FastAPI()

# ---------------- STATIC + TEMPLATES ----------------

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- TESSERACT ----------------

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

# ---------------- HOME ----------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------------- IMAGE PREPROCESS ----------------

def preprocess_image(image):

    img = np.array(image)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray,(5,5),0)

    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpen = cv2.filter2D(thresh,-1,kernel)

    return sharpen

# ---------------- TEXT CLEAN ----------------

def clean_text(text):

    text = text.lower()

    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    return text

# ---------------- MEDICINE MATCH ----------------

def find_medicines(text):

    detected = []

    words = text.split()

    for word in words:

        if len(word) < 4:
            continue

        match = process.extractOne(
            word,
            medicine_list,
            score_cutoff=80
        )

        if match:
            detected.append(match[0])

    return list(set(detected))

# ---------------- DOSE DETECTION ----------------

def extract_doses(text):

    pattern = r'\d+\s*(mg|mcg|g|ml|units)'
    return re.findall(pattern, text)

# ---------------- FREQUENCY DETECTION ----------------

frequency_map = {
    "od":"once daily",
    "bd":"twice daily",
    "tds":"three times daily",
    "qid":"four times daily",
    "sos":"as needed"
}

def detect_frequency(text):

    results = []

    for key,val in frequency_map.items():

        if key in text:
            results.append(val)

    return results

# ---------------- PRESCRIPTION ANALYSIS ----------------

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):

    contents = await file.read()

    image = Image.open(io.BytesIO(contents))

    image = image.resize((1500,1500))

    processed = preprocess_image(image)

    config = r'--oem 3 --psm 6'

    text = pytesseract.image_to_string(
        processed,
        config=config
    )

    text = clean_text(text)

    detected_medicines = find_medicines(text)

    doses = extract_doses(text)

    frequencies = detect_frequency(text)

    # ---------------- INTERACTIONS ----------------

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

    polypharmacy = len(detected_medicines) >= 5

    dashboard = {
        "total_medicines": len(detected_medicines),
        "polypharmacy": polypharmacy
    }

    return {
        "extracted_text": text,
        "medicines_detected": detected_medicines,
        "doses_detected": doses,
        "frequency_detected": frequencies,
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

        txt = f"{i['drug1']} + {i['drug2']} : {i['severity']} risk"

        c.drawString(60, y, txt)

        y -= 20

    c.save()

    return FileResponse(file_name)
