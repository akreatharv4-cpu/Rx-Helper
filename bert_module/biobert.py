from pathlib import Path
from typing import List
import json
import re

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rapidfuzz import process, fuzz

# OCR imports
try:
    from ocr import ocr_image_bytes, ocr_pdf_bytes
except Exception as e:
    print(f"⚠ OCR import failed: {e}")
    ocr_image_bytes = None
    ocr_pdf_bytes = None

# BioBERT extractor
try:
    from bert_module.extractor import extract_clean_drugs
except Exception as e:
    print(f"⚠ BioBERT import failed: {e}")
    extract_clean_drugs = None

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Rx-Helper Clinical Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC + TEMPLATES ----------------
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(templates_dir))

# ---------------- LOAD DATABASE FILES ----------------

def load_csv(filename: str) -> pd.DataFrame:
    path = BASE_DIR / filename
    try:
        return pd.read_csv(path)
    except Exception:
        print(f"⚠ Missing file: {path}")
        return pd.DataFrame()


df_meds = load_csv("medicines.csv")
interactions_df = load_csv("drug_interactions.csv")
dosage_df = load_csv("dosage_reference.csv")
classes_df = load_csv("drug_classes.csv")

try:
    with open(BASE_DIR / "abbreviations.json", "r", encoding="utf-8") as f:
        ABBR = json.load(f)
except Exception:
    ABBR = {}

# ---------------- PREPARE MEDICINE LIST ----------------

if not df_meds.empty:
    med_names = df_meds.iloc[:, 0].dropna().astype(str).str.lower().tolist()
else:
    med_names = []

# dosage lookup
dosage_lookup = {}
if not dosage_df.empty:
    for _, row in dosage_df.iterrows():
        drug = str(row.get("drug", "")).strip().lower()
        max_daily_mg = row.get("max_daily_mg", None)
        if drug and pd.notna(max_daily_mg):
            dosage_lookup[drug] = float(max_daily_mg)

# class lookup
class_lookup = {}
if not classes_df.empty:
    for _, row in classes_df.iterrows():
        drug = str(row.get("drug", "")).strip().lower()
        drug_class = str(row.get("class", "")).strip()
        if drug:
            class_lookup[drug] = drug_class

# ---------------- DOSAGE FORM WORDS ----------------

FORM_WORDS = [
    "tab", "tablet", "tabs",
    "cap", "capsule", "caps",
    "inj", "injection",
    "syp", "syrup",
    "susp", "suspension",
    "cream", "ointment",
    "drops", "drop",
    "inhaler"
]

# ---------------- TEXT CLEANING ----------------

def expand_abbreviations(text: str) -> str:
    for k, v in ABBR.items():
        text = re.sub(rf"\b{re.escape(str(k))}\b", str(v), text, flags=re.IGNORECASE)
    return text


def clean_text(text: str) -> str:
    text = text.lower()
    tokens = text.split()

    filtered = []
    for t in tokens:
        if t in FORM_WORDS:
            continue
        filtered.append(t)

    return " ".join(filtered)

# ---------------- BIOBERT + MEDICINE DETECTION ----------------

def detect_medicines(text: str) -> List[str]:
    detected = []

    if extract_clean_drugs is not None and med_names:
        try:
            biobert_drugs = extract_clean_drugs(text)

            for drug in biobert_drugs:
                drug = str(drug).strip().lower()
                if not drug:
                    continue

                match = process.extractOne(
                    drug,
                    med_names,
                    scorer=fuzz.token_set_ratio
                )

                if match and match[1] > 85:
                    if match[0] not in detected:
                        detected.append(match[0])
                elif drug in med_names:
                    if drug not in detected:
                        detected.append(drug)
        except Exception as e:
            print(f"⚠ BioBERT detection failed, using fallback: {e}")

    if not detected and med_names:
        text_clean = clean_text(text)
        tokens = text_clean.split()

        for token in tokens:
            match = process.extractOne(
                token,
                med_names,
                scorer=fuzz.token_set_ratio
            )

            if match and match[1] > 85:
                if match[0] not in detected:
                    detected.append(match[0])

    return detected

# ---------------- DOSE EXTRACTION ----------------

def extract_doses(text: str):
    doses = {}
    text = text.lower()

    matches = re.findall(r"([a-zA-Z][a-zA-Z0-9\-]*)\s*(\d+(?:\.\d+)?)\s*mg", text)

    for drug, dose in matches:
        match = process.extractOne(
            drug,
            med_names,
            scorer=fuzz.token_set_ratio
        )

        if match and match[1] > 80:
            doses[match[0]] = float(dose)

    return doses

# ---------------- DOSE VALIDATION ----------------

def check_dosage(doses):
    warnings = []

    for drug, dose in doses.items():
        if drug in dosage_lookup and dose > dosage_lookup[drug]:
            warnings.append({
                "drug": drug,
                "dose": dose,
                "limit": dosage_lookup[drug],
                "warning": "Dose exceeds recommended maximum"
            })

    return warnings

# ---------------- DRUG CLASS ----------------

def get_drug_classes(meds):
    result = {}
    for m in meds:
        result[m] = class_lookup.get(m, "Unknown")
    return result

# ---------------- INTERACTION CHECK ----------------

def check_interactions(meds):
    alerts = []

    if interactions_df.empty or len(meds) < 2:
        return alerts

    df = interactions_df.copy()

    if "drug1" not in df.columns or "drug2" not in df.columns:
        return alerts

    df["drug1"] = df["drug1"].astype(str).str.lower()
    df["drug2"] = df["drug2"].astype(str).str.lower()

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            d1 = str(meds[i]).lower()
            d2 = str(meds[j]).lower()

            result = df[
                ((df["drug1"] == d1) & (df["drug2"] == d2)) |
                ((df["drug1"] == d2) & (df["drug2"] == d1))
            ]

            if not result.empty:
                row = result.iloc[0]
                severity = row.get("severity", "Moderate")
                message = row.get("message", "Interaction detected")

                alerts.append({
                    "drug1": d1,
                    "drug2": d2,
                    "severity": severity,
                    "message": message
                })

    return alerts

# ---------------- OCR API ----------------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if ocr_image_bytes is None or ocr_pdf_bytes is None:
        raise HTTPException(status_code=500, detail="OCR module is not available")

    try:
        content = await file.read()

        if file.filename.lower().endswith(".pdf"):
            text = ocr_pdf_bytes(content)
        else:
            text = ocr_image_bytes(content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    text = expand_abbreviations(text)

    medicines = detect_medicines(text)
    interactions = check_interactions(medicines)
    doses = extract_doses(text)
    dose_warnings = check_dosage(doses)
    drug_classes = get_drug_classes(medicines)

    return {
        "medicines_detected": medicines,
        "drug_classes": drug_classes,
        "drug_interactions": interactions,
        "dose_warnings": dose_warnings,
        "raw_text": text
    }

# ---------------- INDEX PAGE ----------------

@app.get("/")
async def index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return {
            "status": "working",
            "template_error": str(e)
        }
