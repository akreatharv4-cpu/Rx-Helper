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

# Import corrected functions
from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI()

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Load CSVs
try:
    interactions = pd.read_csv("drug_interactions.csv")
    interactions["drug1"] = interactions["drug1"].str.lower()
    interactions["drug2"] = interactions["drug2"].str.lower()
    medicine_list = pd.read_csv("medicines.csv")["medicine_name"].str.lower().tolist()
except:
    interactions = pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])
    medicine_list = []

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):
    contents = await file.read()
    if file.filename.lower().endswith(".pdf"):
        full_text = ocr_pdf_bytes(contents)
    else:
        full_text = ocr_image_bytes(contents)
    
    clean_text = re.sub(r'[^a-z0-9\s]', ' ', full_text.lower())
    detected_meds = []
    for word in clean_text.split():
        if len(word) > 3:
            match = process.extractOne(word, medicine_list, score_cutoff=85)
            if match: detected_meds.append(match[0])
    
    detected_meds = list(set(detected_meds))
    
    results = []
    for i in range(len(detected_meds)):
        for j in range(i + 1, len(detected_meds)):
            d1, d2 = detected_meds[i], detected_meds[j]
            match = interactions[((interactions["drug1"] == d1) & (interactions["drug2"] == d2)) | 
                                 ((interactions["drug1"] == d2) & (interactions["drug2"] == d1))]
            if not match.empty:
                row = match.iloc[0]
                results.append({"drug1": d1, "drug2": d2, "severity": row["severity"], "message": row["message"]})

    return {
        "medicines_detected": detected_meds,
        "drug_interactions": results,
        "extracted_text": full_text
    }
