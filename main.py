from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import re
from rapidfuzz import process

# Import the lightweight Tesseract functions
from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI()

# --- SETUP ---
for folder in ["static", "templates"]:
    if not os.path.exists(folder): os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- DATA LOADING ---
def load_csv(file, cols):
    if os.path.exists(file): return pd.read_csv(file)
    return pd.DataFrame(columns=cols)

interactions = load_csv("drug_interactions.csv", ["drug1", "drug2", "severity", "message"])
if not interactions.empty:
    interactions["drug1"] = interactions["drug1"].str.lower()
    interactions["drug2"] = interactions["drug2"].str.lower()

medicines = load_csv("medicines.csv", ["medicine_name"])
medicine_list = medicines["medicine_name"].str.lower().tolist() if not medicines.empty else []

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):
    contents = await file.read()
    
    # Perform OCR using Tesseract (Memory Efficient)
    if file.filename.lower().endswith(".pdf"):
        full_text = ocr_pdf_bytes(contents)
    else:
        full_text = ocr_image_bytes(contents)
    
    clean_text = re.sub(r'[^a-z0-9\s]', ' ', full_text.lower())
    
    # Match Medicines from your CSV
    detected_meds = []
    for word in clean_text.split():
        if len(word) > 3:
            match = process.extractOne(word, medicine_list, score_cutoff=85)
            if match: detected_meds.append(match[0])
    detected_meds = list(set(detected_meds))

    # Check Interactions
    interaction_results = []
    for i in range(len(detected_meds)):
        for j in range(i + 1, len(detected_meds)):
            d1, d2 = detected_meds[i], detected_meds[j]
            match = interactions[((interactions["drug1"] == d1) & (interactions["drug2"] == d2)) | 
                                 ((interactions["drug1"] == d2) & (interactions["drug2"] == d1))]
            if not match.empty:
                row = match.iloc[0]
                interaction_results.append({
                    "drug1": d1, 
                    "drug2": d2, 
                    "severity": row.get("severity", "Major"), 
                    "message": row.get("message", "Interaction detected")
                })

    # Prepare data for your Javascript Dashboard
    return {
        "medicines_detected": detected_meds,
        "drug_interactions": interaction_results,
        "dashboard": {
            "total_medicines": len(detected_meds),
            "polypharmacy": len(detected_meds) >= 5,
            "antibiotic_count": 0, # Placeholders for your script
            "injection_count": 0
        },
        "drug_classification": {m: "General Medicine" for m in detected_meds} # Matches your table
    }

@app.post("/report")
async def generate_report(data: dict):
    # Simplified report logic for brevity
    return {"message": "Report logic triggered"}
