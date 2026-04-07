from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ocr import ocr_image_bytes, ocr_pdf_bytes, extract_clean_drugs
from pathlib import Path
import pandas as pd
from rapidfuzz import process, fuzz
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Mount static files (for your CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent
MEDICINE_PATH = BASE_DIR / "medicines_master.csv"

# ---------------- DATA LOADING ---------------- #

def load_medicines():
    try:
        # Loading CSV: name, class, form, is_generic, is_antibiotic
        df = pd.read_csv(MEDICINE_PATH) 
        df["name"] = df["name"].str.lower().str.strip()
        return df
    except Exception as e:
        print("⚠ Medicine load error:", e)
        return pd.DataFrame(columns=["name", "class", "form", "is_generic", "is_antibiotic"])

medicine_df = load_medicines()
medicine_list = medicine_df["name"].tolist()

# ---------------- WHO INDICATORS LOGIC ---------------- #

def calculate_who_indicators(detected_meds):
    total_drugs = len(detected_meds)
    if total_drugs == 0:
        return {"drugs_per_encounter": 0, "pc_generic": 0, "pc_antibiotic": 0, "pc_injection": 0}

    # Filter DB for detected drugs (handling fuzzy matches)
    subset = medicine_df[medicine_df["name"].isin([m.lower() for m in detected_meds])]
    
    generics_count = subset[subset["is_generic"] == 1].shape[0]
    antibiotics_count = subset[subset["is_antibiotic"] == 1].shape[0]
    
    # Check for 'inj' in the form column
    injections_count = subset[subset["form"].str.contains("inj", case=False, na=False)].shape[0]

    return {
        "drugs_per_encounter": total_drugs,
        "pc_generic": round((generics_count / total_drugs) * 100, 1),
        "pc_antibiotic": round((antibiotics_count / total_drugs) * 100, 1),
        "pc_injection": round((injections_count / total_drugs) * 100, 1)
    }

# ---------------- CORE ANALYSIS PIPELINE ---------------- #

def run_analysis_pipeline(text: str):
    # 1. Extract raw names using BioBERT logic in ocr.py
    raw_meds = extract_clean_drugs(text)
    
    # 2. Fuzzy match against CSV database (85% threshold)
    final_meds = []
    for m in raw_meds:
        if medicine_list:
            match = process.extractOne(m.lower(), medicine_list, scorer=fuzz.ratio)
            if match and match[1] >= 85:
                final_meds.append(match[0].title()) # Add proper case
                continue
        final_meds.append(m.title()) 

    # 3. Calculate WHO Data
    who_data = calculate_who_indicators(final_meds)
    
    return {
        "success": True,
        "medicines": final_meds,
        "who_indicators": who_data,
        "raw_text": text
    }

# ---------------- DATA MODELS ---------------- #

class ChatRequest(BaseModel):
    message: str
    context_meds: Optional[List[str]] = []
    patient_info: Optional[dict] = {}

# ---------------- ROUTES ---------------- #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze-text")
async def analyze_text(data: dict = Body(...)):
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    return run_analysis_pipeline(text)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    filename = (file.filename or "").lower()
    
    # Route to correct OCR function
    text = ocr_pdf_bytes(content) if filename.endswith(".pdf") else ocr_image_bytes(content)
        
    return run_analysis_pipeline(text)

@app.post("/chat")
async def clinical_chat(data: ChatRequest):
    user_query = data.message.lower()
    meds_on_hand = ", ".join(data.context_meds) if data.context_meds else "None detected"
    
    # Clinical Logic Switch
    if "dose" in user_query:
        reply = f"For {meds_on_hand}, dosage must be checked against CrCl (Renal) and Age. WHO suggests cautious prescribing in pediatrics/geriatrics."
    elif "generic" in user_query or "alternative" in user_query:
        reply = "WHO core indicators prioritize generic prescribing to reduce healthcare costs and improve medicine availability."
    else:
        reply = f"I have reviewed the prescription ({meds_on_hand}). Do you need info on drug-drug interactions or counseling points?"

    return {"reply": reply}