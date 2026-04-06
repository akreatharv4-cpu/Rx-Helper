from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import re  
from ocr import ocr_image_bytes, ocr_pdf_bytes, extract_clean_drugs
from pathlib import Path
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
            "high": "Severe",
            "major": "Severe",
            "severe": "Severe",
            "moderate": "Moderate",
            "medium": "Moderate",
            "low": "Mild",
            "mild": "Mild",
        }

        if "severity" in df.columns:
            df["severity"] = (
                df["severity"]
                .astype(str)
                .str.strip()
                .str.lower()
                .map(severity_map)
                .fillna("Moderate")
            )
        else:
            df["severity"] = "Moderate"

        if "message" not in df.columns:
            if "description" in df.columns:
                df["message"] = df["description"].astype(str)
            else:
                df["message"] = "Drug interaction detected"

        return df[["drug1", "drug2", "severity", "message"]]

    except Exception as e:
        print("⚠ Interaction database error:", e)
        return pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])


interactions_df = load_interactions()


def severity_icon(severity):
    return {
        "Severe": "🔴",
        "Moderate": "🟠",
        "Mild": "🟡"
    }.get(severity, "⚪")


def detect_medicines(text: str):
    """
    Splits the cleaned OCR text into a list of individual medicines.
    Assumes medicines are separated by newlines, commas, or bullets.
    """
    if not text:
        return []
        
    # 1. Get the cleaned text from your ocr.py utility
    cleaned_text = extract_clean_drugs(text)
    
    # 2. Split by common delimiters (newline, comma, semicolon)
    # This turns "Aspirin, Panadol" into ["Aspirin", "Panadol"]
    raw_list = re.split(r'[\n,;•]', cleaned_text)
    
    # 3. Clean up each item and remove empty strings
    med_list = [m.strip() for m in raw_list if m.strip()]
    
    return med_list


def check_interactions(medicine_list):
    alerts = []

    if interactions_df.empty or not medicine_list:
        return alerts

    meds = []
    seen_meds = set()

    for m in medicine_list:
        if not m:
            continue
        cleaned = str(m).lower().strip()
        if cleaned and cleaned not in seen_meds:
            seen_meds.add(cleaned)
            meds.append(cleaned)

    seen_pairs = set()

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            drug1 = meds[i]
            drug2 = meds[j]
            key = tuple(sorted([drug1, drug2]))

            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            result = interactions_df[
                ((interactions_df["drug1"] == drug1) & (interactions_df["drug2"] == drug2)) |
                ((interactions_df["drug1"] == drug2) & (interactions_df["drug2"] == drug1))
            ]

            if not result.empty:
                row = result.iloc[0]
                alerts.append({
                    "drug1": drug1.upper(),
                    "drug2": drug2.upper(),
                    "severity": row["severity"],
                    "message": row["message"],
                    "icon": severity_icon(row["severity"])
                })

    return alerts


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test")
async def test():
    return {"status": "working"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = (file.filename or "").lower()

        print("📁 FILE RECEIVED:", filename)

        if filename.endswith(".pdf"):
            text = ocr_pdf_bytes(content)
            source_type = "pdf"
        else:
            text = ocr_image_bytes(content)
            source_type = "image"

        if not text or len(text.strip()) == 0:
            raise Exception("OCR returned empty text")

        print("🧾 OCR TEXT:", text[:200])

        meds = detect_medicines(text)
        print("💊 MEDS:", meds)

        interactions = check_interactions(meds)
        print("⚠ INTERACTIONS:", interactions)

        return {
            "success": True,
            "source_type": source_type,
            "medicines_detected": meds,
            "drug_interactions": interactions,
            "dose_warnings": [],
            "drug_classes": {},
            "raw_text": text,
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))