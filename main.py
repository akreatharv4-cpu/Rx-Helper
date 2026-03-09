from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import re
from rapidfuzz import process
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Import your corrected OCR functions from ocr.py
from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI()

# ---------------- RENDER HEALTH CHECK ----------------
# This prevents Render from "timing out" during deployment
@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

# ---------------- STATIC & TEMPLATES ----------------
# This creates the folders if they don't exist yet
for folder in ["static", "templates"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- CORS SETTINGS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATASET LOADING ----------------
try:
    interactions = pd.read_csv("drug_interactions.csv")
    interactions["drug1"] = interactions["drug1"].str.lower()
    interactions["drug2"] = interactions["drug2"].str.lower()
except Exception as e:
    print(f"Interaction data load failed: {e}")
    interactions = pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])

try:
    medicines = pd.read_csv("medicines.csv")
    medicine_list = medicines["medicine_name"].str.lower().tolist()
except Exception as e:
    print(f"Medicine list load failed: {e}")
    medicine_list = []

# ---------------- UTILITY FUNCTIONS ----------------

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text

def find_medicines(text):
    detected = []
    words = text.split()
    for word in words:
        if len(word) < 4:
            continue
        # Using a score_cutoff of 85 to be accurate
        match = process.extractOne(word, medicine_list, score_cutoff=85)
        if match:
            detected.append(match[0])
    return list(set(detected))

# ---------------- ROUTES ----------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename.lower()

    # Call your OCR functions from ocr.py
    if filename.endswith(".pdf"):
        full_text = ocr_pdf_bytes(contents)
    else:
        full_text = ocr_image_bytes(contents)

    text = clean_text(full_text)
    detected_meds = find_medicines(text)

    # Analyze Interactions
    interaction_results = []
    for i in range(len(detected_meds)):
        for j in range(i + 1, len(detected_meds)):
            d1, d2 = detected_meds[i], detected_meds[j]
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

    return {
        "extracted_text": text,
        "medicines_detected": detected_meds,
        "drug_interactions": interaction_results,
        "dashboard": {
            "total_medicines": len(detected_meds),
            "polypharmacy": len(detected_meds) >= 5
        }
    }

@app.post("/report")
def generate_report(data: dict):
    file_name = "clinical_report.pdf"
    c = canvas.Canvas(file_name, pagesize=letter)
    c.drawString(50, 750, "Rx Helper - Pharmacy Clinical Report")
    
    y = 710
    c.drawString(50, y, "Medicines Detected:")
    y -= 20
    for m in data.get("medicines", []):
        c.drawString(70, y, f"- {m}")
        y -= 20
        
    c.save()
    return FileResponse(file_name)
