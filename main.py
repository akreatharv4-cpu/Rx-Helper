from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from pathlib import Path
import pandas as pd
import json
import re

from rapidfuzz import process, fuzz

# ---------------- APP ----------------
app = FastAPI(title="Rx-Helper Clinical Assistant")

BASE_DIR = Path(__file__).resolve().parent

# ---------------- OCR ----------------
try:
    from ocr import ocr_image_bytes, ocr_pdf_bytes
except Exception as e:
    print(f"⚠ OCR import failed: {e}")
    ocr_image_bytes = None
    ocr_pdf_bytes = None

# ---------------- BIOBERT ----------------
try:
    from bert_module.extractor import extract_clean_drugs
except Exception as e:
    print(f"⚠ BioBERT import failed: {e}")
    def extract_clean_drugs(text):
        return []

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC ----------------
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ---------------- LOAD FILES ----------------
def load_csv(filename: str):
    path = BASE_DIR / filename
    try:
        return pd.read_csv(path)
    except:
        print(f"Missing: {filename}")
        return pd.DataFrame()

df_meds = load_csv("medicines.csv")
interactions_df = load_csv("drug_interactions.csv")
dosage_df = load_csv("dosage_reference.csv")
classes_df = load_csv("drug_classes.csv")

try:
    with open(BASE_DIR / "abbreviations.json") as f:
        ABBR = json.load(f)
except:
    ABBR = {}

med_names = []
if not df_meds.empty:
    med_names = df_meds.iloc[:, 0].dropna().astype(str).str.lower().tolist()

# ---------------- FUNCTIONS ----------------
def detect_medicines(text):
    try:
        return extract_clean_drugs(text)
    except:
        return []

# ---------------- ROUTES ----------------
@app.get("/test")
async def test():
    return {"status": "working"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if ocr_image_bytes is None:
        raise HTTPException(500, "OCR not working")

    content = await file.read()

    if file.filename.endswith(".pdf"):
        text = ocr_pdf_bytes(content)
    else:
        text = ocr_image_bytes(content)

    meds = detect_medicines(text)

    return {
        "medicines_detected": meds,
        "drug_classes": {},
        "drug_interactions": [],
        "dose_warnings": [],
        "raw_text": text
    }
@app.get("/test")
async def test():
    return {"status": "working"}
