from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pandas as pd
from rapidfuzz import process, fuzz
from typing import List

from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI(title="Rx-Helper OCR API")

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC + TEMPLATES ----------------

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- LOAD MEDICINE DATABASE ----------------

MEDICINES_CSV = "medicines.csv"

try:
    df_meds = pd.read_csv(MEDICINES_CSV)

    if "name" in df_meds.columns:
        med_names = df_meds["name"].dropna().astype(str).str.lower().tolist()

    elif "medicine" in df_meds.columns:
        med_names = df_meds["medicine"].dropna().astype(str).str.lower().tolist()

    else:
        med_names = df_meds.iloc[:, 0].dropna().astype(str).str.lower().tolist()

except Exception:
    med_names = []
    print("⚠ medicines.csv not found")

# ---------------- LOAD INTERACTION DATABASE ----------------

try:
    interactions_df = pd.read_csv("drug_interactions.csv")
except:
    interactions_df = pd.DataFrame()

# ---------------- MEDICINE DETECTION ----------------


def detect_medicines_from_text(text: str) -> List[str]:

    detected = []

    words = text.lower().split()

    for word in words:

        match = process.extractOne(word, med_names, scorer=fuzz.WRatio)

        if match and match[1] > 85:
            detected.append(match[0])

    return list(set(detected))


# ---------------- INTERACTION CHECK ----------------


def check_interactions(meds: List[str]):

    alerts = []

    if interactions_df.empty:
        return alerts

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):

            d1 = meds[i]
            d2 = meds[j]

            result = interactions_df[
                ((interactions_df["drug1"] == d1) & (interactions_df["drug2"] == d2)) |
                ((interactions_df["drug1"] == d2) & (interactions_df["drug2"] == d1))
            ]

            if not result.empty:

                row = result.iloc[0]

                alerts.append({
                    "drug1": d1,
                    "drug2": d2,
                    "severity": row.get("severity", "Unknown"),
                    "message": row.get("description", "Interaction detected")
                })

    return alerts


# ---------------- OCR UPLOAD API ----------------


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    try:

        content = await file.read()

        if file.filename.lower().endswith(".pdf"):
            text = ocr_pdf_bytes(content)
        else:
            text = ocr_image_bytes(content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    medicines = detect_medicines_from_text(text)

    interactions = check_interactions(medicines)

    return {
        "medicines_detected": medicines,
        "drug_interactions": interactions,
        "raw_text": text
    }


# ---------------- INDEX PAGE ----------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )
