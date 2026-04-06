from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ocr import ocr_image_bytes, ocr_pdf_bytes, extract_clean_drugs
from pathlib import Path
import pandas as pd
from thefuzz import process
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "drug_interactions.csv"


# ---------------- LOAD INTERACTIONS ---------------- #

def load_interactions():
    try:
        df = pd.read_csv(CSV_PATH)

        df["drug1"] = df["drug1"].astype(str).str.lower().str.strip()
        df["drug2"] = df["drug2"].astype(str).str.lower().str.strip()

        if "severity" not in df.columns:
            df["severity"] = "Moderate"

        if "message" not in df.columns:
            df["message"] = "Drug interaction detected"

        return df

    except Exception as e:
        print("⚠ Interaction load error:", e)
        return pd.DataFrame()


interactions_df = load_interactions()


# ---------------- TEXT CLEANING ---------------- #

def clean_text(text: str):
    """
    Clean noisy OCR text
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # remove symbols
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------- MEDICINE DETECTION ---------------- #

def detect_medicines(text: str):
    if not text:
        return []

    # Clean OCR noise
    text = clean_text(text)

    # Extract drugs (BioBERT / OCR logic)
    meds = extract_clean_drugs(text)

    # Normalize
    meds = list(set([m.lower().strip() for m in meds if len(m) > 2]))

    print("💊 DETECTED MEDS:", meds)

    return meds


# ---------------- INTERACTION CHECK ---------------- #

def check_interactions(medicine_list):
    alerts = []

    if interactions_df.empty or not medicine_list:
        return alerts

    all_known_drugs = list(set(
        interactions_df["drug1"].tolist() +
        interactions_df["drug2"].tolist()
    ))

    matched = []

    for m in medicine_list:
        match = process.extractOne(m, all_known_drugs)

        # safer threshold
        if match and match[1] > 80:
            matched.append(match[0])

    matched = list(set(matched))
    seen = set()

    for i in range(len(matched)):
        for j in range(i + 1, len(matched)):
            d1, d2 = matched[i], matched[j]
            key = tuple(sorted([d1, d2]))

            if key in seen:
                continue
            seen.add(key)

            res = interactions_df[
                ((interactions_df["drug1"] == d1) & (interactions_df["drug2"] == d2)) |
                ((interactions_df["drug1"] == d2) & (interactions_df["drug2"] == d1))
            ]

            if not res.empty:
                row = res.iloc[0]
                alerts.append({
                    "drug1": d1.upper(),
                    "drug2": d2.upper(),
                    "severity": row["severity"],
                    "message": row["message"]
                })

    print("⚠ INTERACTIONS:", alerts)

    return alerts


# ---------------- ROUTES ---------------- #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = (file.filename or "").lower()

        print(f"\n📁 FILE: {filename}")

        # OCR
        text = ocr_pdf_bytes(content) if filename.endswith(".pdf") else ocr_image_bytes(content)

        print("\n===== RAW OCR TEXT =====\n")
        print(text[:1000])   # limit output
        print("\n========================\n")

        if not text:
            raise Exception("OCR returned empty text")

        # detect medicines
        meds = detect_medicines(text)

        # interactions
        interactions = check_interactions(meds)

        return {
            "success": True,
            "medicines_detected": meds,
            "drug_interactions": interactions,
            "dose_warnings": [],
            "drug_classes": {},
            "raw_text": text,
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))