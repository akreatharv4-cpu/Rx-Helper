from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ocr import ocr_image_bytes, ocr_pdf_bytes
from pathlib import Path
import pandas as pd
from rapidfuzz import process, fuzz
import re

app = FastAPI()
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent

INTERACTION_PATH = BASE_DIR / "drug_interactions.csv"
MEDICINE_PATH = BASE_DIR / "medicines.csv"

# ---------------- LOAD DATA ---------------- #

def load_medicines():
    try:
        df = pd.read_csv(MEDICINE_PATH, header=None)
        df.columns = ["name", "class", "form", "dose", "frequency"]
        df["name"] = df["name"].str.lower().str.strip()
        return df
    except Exception as e:
        print("⚠ Medicine load error:", e)
        return pd.DataFrame()

def load_interactions():
    try:
        df = pd.read_csv(INTERACTION_PATH)

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

medicine_df = load_medicines()
medicine_list = medicine_df["name"].tolist()
interactions_df = load_interactions()


# ---------------- TEXT CLEAN ---------------- #

def clean_text(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------- MEDICINE DETECTION ---------------- #

def detect_medicines(text: str):
    if not text:
        return []

    text = clean_text(text)
    words = re.findall(r"[a-z]{3,}", text)

    detected = set()

    for word in words:
        match = process.extractOne(
            word,
            medicine_list,
            scorer=fuzz.ratio   # 🔥 better matching
        )

        if match:
            name, score, _ = match

            if score >= 85:
                detected.add(name)

    meds = list(detected)
    print("💊 CLEAN MEDS:", meds)

    return meds


# ---------------- DRUG CLASS ---------------- #

def get_drug_classes(meds):
    classes = {}

    for m in meds:
        row = medicine_df[medicine_df["name"] == m]

        if not row.empty:
            classes[m] = row.iloc[0]["class"]
        else:
            classes[m] = "Unknown"

    return classes


# ---------------- DOSE EXTRACTION ---------------- #

def extract_doses(text):
    doses = re.findall(r"\b\d+\s?(mg|mcg|g|ml)\b", text.lower())
    return list(set(doses))


# ---------------- INTERACTION CHECK ---------------- #

def check_interactions(medicine_list):
    alerts = []

    if interactions_df.empty or not medicine_list:
        return alerts

    meds = list(set([m.lower().strip() for m in medicine_list]))

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            d1, d2 = meds[i], meds[j]

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

        print("\n===== OCR TEXT =====\n", text[:500])

        if not text:
            raise Exception("OCR returned empty text")

        # medicines
        meds = detect_medicines(text)

        # classes
        classes = get_drug_classes(meds)

        # interactions
        interactions = check_interactions(meds)

        # dose extraction
        doses = extract_doses(text)

        return {
            "success": True,
            "medicines_detected": meds,
            "drug_classes": classes,
            "drug_interactions": interactions,
            "dose_warnings": doses,
            "raw_text": text,
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))