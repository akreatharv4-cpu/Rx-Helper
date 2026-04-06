from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import re
import spacy
from thefuzz import process  # For fuzzy matching OCR typos
from ocr import ocr_image_bytes, ocr_pdf_bytes, extract_clean_drugs
from pathlib import Path
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load the SpaCy model you successfully installed
try:
    nlp = spacy.load("en_core_web_md")
except:
    # Fallback if model loading fails
    nlp = None

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "drug_interactions.csv"

def load_interactions():
    try:
        df = pd.read_csv(CSV_PATH)
        if "drug1" not in df.columns or "drug2" not in df.columns:
            raise ValueError("drug_interactions.csv must contain drug1 and drug2 columns")

        df["drug1"] = df["drug1"].astype(str).str.lower().str.strip()
        df["drug2"] = df["drug2"].astype(str).str.lower().str.strip()

        severity_map = {
            "high": "Severe", "major": "Severe", "severe": "Severe",
            "moderate": "Moderate", "medium": "Moderate",
            "low": "Mild", "mild": "Mild",
        }

        if "severity" in df.columns:
            df["severity"] = df["severity"].astype(str).str.strip().str.lower().map(severity_map).fillna("Moderate")
        else:
            df["severity"] = "Moderate"

        if "message" not in df.columns:
            df["message"] = df["description"].astype(str) if "description" in df.columns else "Drug interaction detected"

        return df[["drug1", "drug2", "severity", "message"]]
    except Exception as e:
        print("⚠ Interaction database error:", e)
        return pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])

interactions_df = load_interactions()

def severity_icon(severity):
    return {"Severe": "🔴", "Moderate": "🟠", "Mild": "🟡"}.get(severity, "⚪")

def detect_medicines(text: str):
    """
    Uses SpaCy NER to find drug names and cleans up OCR garble.
    """
    if not text or not nlp:
        return []
    
    # Run NER model
    doc = nlp(text)
    
    # NER Extraction: Filter for entities that look like drug products/brands
    ner_meds =]
    
    # Fallback/Manual Extraction: Use regex to split cleaned text
    cleaned_text = extract_clean_drugs(text)
    split_meds = [m.strip() for m in re.split(r'[\n,;•]', cleaned_text) if len(m.strip()) > 3]
    
    # Combine results, remove duplicates, and title-case them
    combined = list(set(ner_meds + split_meds))
    return [m.title() for m in combined if len(m) > 2]

def check_interactions(medicine_list):
    """
    Uses Fuzzy Matching to find interactions even with OCR typos.
    """
    alerts = []
    if interactions_df.empty or not medicine_list:
        return alerts

    # Get a unique list of all drugs known in our CSV
    all_known_drugs = list(set(interactions_df["drug1"].tolist() + interactions_df["drug2"].tolist()))
    
    # 1. Map messy OCR names to the closest real drug name in our CSV
    matched_meds = []
    for m in medicine_list:
        # If match is > 85% similar, use the CSV's correct spelling
        match_tuple = process.extractOne(m.lower(), all_known_drugs)
        if match_tuple and match_tuple[1] > 85:
            matched_meds.append(match_tuple[0])

    matched_meds = list(set(matched_meds))
    seen_pairs = set()

    # 2. Check pairs of matched drugs
    for i in range(len(matched_meds)):
        for j in range(i + 1, len(matched_meds)):
            d1, d2 = matched_meds[i], matched_meds[j]
            key = tuple(sorted([d1, d2]))

            if key in seen_pairs: continue
            seen_pairs.add(key)

            res = interactions_df[
                ((interactions_df["drug1"] == d1) & (interactions_df["drug2"] == d2)) |
                ((interactions_df["drug1"] == d2) & (interactions_df["drug2"] == d1))
            ]

            if not res.empty:
                row = res.iloc[0]
                alerts.append({
                    "drug1": d1.upper(), "drug2": d2.upper(),
                    "severity": row["severity"], "message": row["message"],
                    "icon": severity_icon(row["severity"])
                })
    return alerts

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = (file.filename or "").lower()
        
        text = ocr_pdf_bytes(content) if filename.endswith(".pdf") else ocr_image_bytes(content)
        if not text: raise Exception("OCR returned empty text")

        meds = detect_medicines(text)
        interactions = check_interactions(meds)

        return {
            "success": True,
            "medicines_detected": meds,
            "drug_interactions": interactions,
            "raw_text": text,
        }
    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))