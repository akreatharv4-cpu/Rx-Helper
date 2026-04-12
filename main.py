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
import re  # NEW: Required for cleaning up messy OCR text

# --- NEW IMPORTS FOR AI & INTERACTIONS ---
from transformers import AutoTokenizer, AutoModel
import torch
from interaction_checker import check_interactions  # Pulling in your custom logic!

app = FastAPI()

# Mount static files (for your CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent
MEDICINE_PATH = BASE_DIR / "medicines_master.csv"
DOSAGE_PATH = BASE_DIR / "dosage_reference.csv"  # NEW: Dosage checking

# ---------------- AI MODELS (Hugging Face) ---------------- #
print("Booting AI Engine: Loading Transformers...")
try:
    clinical_tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    clinical_model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    
    bio_tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-v1.1")
    bio_model = AutoModel.from_pretrained("dmis-lab/biobert-v1.1")
    
    print("✅ BioBERT and ClinicalBERT loaded successfully!")
except Exception as e:
    print(f"⚠ AI Model load error: {e}")
    clinical_model, bio_model = None, None

# ---------------- DATA LOADING ---------------- #

def load_medicines():
    try:
        df = pd.read_csv(MEDICINE_PATH) 
        if "drug_name" in df.columns:
            df = df.rename(columns={"drug_name": "name"})
        df["name"] = df["name"].str.lower().str.strip()
        return df
    except Exception as e:
        print("⚠ Medicine load error:", e)
        return pd.DataFrame(columns=["name", "class", "is_antibiotic", "is_injection", "is_edl", "is_generic"])

def load_dosages():
    """NEW: Loads max daily limits into a dictionary for instant lookup."""
    try:
        df = pd.read_csv(DOSAGE_PATH)
        df["drug_name"] = df["drug_name"].str.lower().str.strip()
        return dict(zip(df["drug_name"], df["max_daily_mg"]))
    except Exception as e:
        print("⚠ Dosage load error:", e)
        return {}

medicine_df = load_medicines()
medicine_list = medicine_df["name"].tolist()
dosage_dict = load_dosages()

# ---------------- WHO INDICATORS LOGIC ---------------- #

def calculate_who_indicators(detected_meds):
    total_drugs = len(detected_meds)
    if total_drugs == 0:
        return {"drugs_per_encounter": 0, "pc_generic": 0, "pc_antibiotic": 0, "pc_injection": 0, "pc_edl": 0}

    subset = medicine_df[medicine_df["name"].isin([m.lower() for m in detected_meds])]
    
    # UPGRADE: Safe column checks to prevent key errors
    generics_count = subset[subset["is_generic"] == 1].shape[0] if "is_generic" in subset.columns else 0
    antibiotics_count = subset[subset["is_antibiotic"] == 1].shape[0] if "is_antibiotic" in subset.columns else 0
    injections_count = subset[subset["is_injection"] == 1].shape[0] if "is_injection" in subset.columns else 0
    edl_count = subset[subset["is_edl"] == 1].shape[0] if "is_edl" in subset.columns else 0

    return {
        "drugs_per_encounter": total_drugs,
        "pc_generic": round((generics_count / total_drugs) * 100, 1),
        "pc_antibiotic": round((antibiotics_count / total_drugs) * 100, 1),
        "pc_injection": round((injections_count / total_drugs) * 100, 1),
        "pc_edl": round((edl_count / total_drugs) * 100, 1)  # Added to output
    }

# ---------------- DOSE CALCULATION HELPER ---------------- #

def extract_dose_and_frequency(text, drug_name):
    """
    Scans text near a detected drug to calculate daily intake.
    Example: 'Paracetamol 500mg TID' -> 1500mg
    """
    text = text.lower()
    start_idx = text.find(drug_name.lower())
    if start_idx == -1: return 0, 0
    
    # Look at the text immediately following the drug name
    context = text[start_idx : start_idx + 70]
    
    # 1. Extract Strength (e.g., 500mg, 1g)
    strength = 0
    strength_match = re.search(r'(\d+(?:\.\d+)?)\s*(mg|g|mcg)', context)
    if strength_match:
        val = float(strength_match.group(1))
        unit = strength_match.group(2)
        strength = val * 1000 if unit == 'g' else val # Convert g to mg
        
    # 2. Extract Frequency (Clinical Shorthand)
    freq = 1 
    if any(x in context for x in ["tid", "t.i.d", "3 times", "tds"]): freq = 3
    elif any(x in context for x in ["bid", "b.i.d", "2 times", "bd"]): freq = 2
    elif any(x in context for x in ["qid", "q.i.d", "4 times"]): freq = 4
    elif any(x in context for x in ["od", "o.d", "once daily", "hs"]): freq = 1
    
    return strength, freq

# ---------------- UPDATED CORE ANALYSIS PIPELINE ---------------- #

def run_analysis_pipeline(text: str):
    cleaned_text = text.replace("\n", " ").lower()

    # 1. Extract raw names
    raw_meds = extract_clean_drugs(text)
    
    # 2. NOISE FILTER
    stop_words = {
        "prescription", "tablet", "tablets", "capsule", "syrup", "syp", 
        "dr", "patient", "dose", "daily", "mg", "ml", "tab", "clinic", 
        "formate", "medical", "india", "name", "mbbs", "md", "hospital"
    }
    filtered_meds = [m for m in raw_meds if m.lower().strip() not in stop_words]
    
    final_meds = []
    overdose_alerts = [] # NEW: To store calculated dose warnings
    
    # 3. FUZZY MATCHING & DOSE AUDITING
    for m in filtered_meds:
        clean_m = re.sub(r'\b(tablet|cap|syp|injection|inj|syrup|hcl|mg)\b.*', '', m, flags=re.IGNORECASE).strip()
        if not clean_m: continue

        if medicine_list:
            match = process.extractOne(clean_m.lower(), medicine_list, scorer=fuzz.WRatio)
            if match and match[1] >= 72:
                drug_name = match[0].title()
                final_meds.append(drug_name)
                
                # --- ACTIVE AUDIT: Calculate Daily Total vs CSV Limit ---
                strength, freq = extract_dose_and_frequency(cleaned_text, drug_name)
                daily_total = strength * freq
                max_limit = dosage_dict.get(drug_name.lower(), 0)
                
                if max_limit > 0 and daily_total > max_limit:
                    overdose_alerts.append({
                        "drug1": drug_name,
                        "drug2": "Limit Exceeded",
                        "severity": "Severe",
                        "message": f"🚨 OVERDOSE ALERT: Prescribed {daily_total}mg/day. Safe limit is {max_limit}mg/day."
                    })
                continue
        
        if len(clean_m) > 3:
            final_meds.append(clean_m.title()) 

    # 4. FALLBACK & DEDUPLICATION
    for db_med in medicine_list:
        if len(db_med) > 4 and db_med.title() not in final_meds:
            if db_med.lower() in cleaned_text:
                final_meds.append(db_med.title())

    final_meds = list(set(final_meds))

    # 5. DATA MERGING
    who_data = calculate_who_indicators(final_meds)
    
    # Combine drug-drug interaction alerts + overdose alerts
    interaction_alerts = check_interactions(final_meds)
    all_safety_alerts = interaction_alerts + overdose_alerts
    
    dosage_limits = {
        med: f"{dosage_dict.get(med.lower(), 'N/A')} mg/day" 
        for med in final_meds
    }

    return {
        "success": True,
        "medicines": final_meds,
        "who_indicators": who_data,
        "interactions": all_safety_alerts, # Now sends both types of alerts
        "max_dosages": dosage_limits,
        "raw_text": text
    }
    
    # 3. AGGRESSIVE FUZZY MATCHING (OCR Correction)
    final_meds = []
    for m in filtered_meds:
        # Strip trailing words like "Tablet'et" or "HCL" from the extracted string
        clean_m = re.sub(r'\b(tablet|cap|syp|injection|inj|syrup|hcl|mg)\b.*', '', m, flags=re.IGNORECASE).strip()
        
        if not clean_m:
            continue

        if medicine_list:
            # UPGRADE: Using WRatio instead of ratio, and dropping threshold to 72%
            # This allows "Azithicryyin" to safely snap to "Azithromycin"
            match = process.extractOne(clean_m.lower(), medicine_list, scorer=fuzz.WRatio)
            if match and match[1] >= 72:
                final_meds.append(match[0].title()) # Add the correctly spelled DB name
                continue
        
        # Only keep the unknown word if it's longer than 3 letters
        if len(clean_m) > 3:
            final_meds.append(clean_m.title()) 

    # 4. FALLBACK SCAN: If BioBERT completely missed a messy drug, scan the raw text
    for db_med in medicine_list:
        if len(db_med) > 4 and db_med.title() not in final_meds:
            if db_med.lower() in cleaned_text:
                final_meds.append(db_med.title())

    # 5. Deduplicate the final list
    final_meds = list(set(final_meds))

    # 6. Calculate WHO Data
    who_data = calculate_who_indicators(final_meds)
    
    # 7. Check Drug-Drug Interactions
    interactions_alerts = check_interactions(final_meds)
    
    # 8. Attach Maximum Daily Dosages
    dosage_limits = {
        med: f"{dosage_dict.get(med.lower(), 'N/A')} mg/day" 
        for med in final_meds
    }

    return {
        "success": True,
        "medicines": final_meds,
        "who_indicators": who_data,
        "interactions": interactions_alerts,
        "max_dosages": dosage_limits,
        "raw_text": text
    }

# ---------------- DATA MODELS ---------------- #

# NEW: Add this model to handle the /analyze-text request structure
class AnalysisRequest(BaseModel):
    text: str

class ChatRequest(BaseModel):
    message: str
    context_meds: Optional[List[str]] = []
    patient_info: Optional[dict] = {}

# ---------------- ROUTES ---------------- #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# UPGRADED: Using AnalysisRequest model fixes the 422 error
@app.post("/analyze-text")
async def analyze_text(data: AnalysisRequest): 
    # data.text is now automatically validated and extracted
    if not data.text:
        raise HTTPException(status_code=400, detail="No text provided")
    return run_analysis_pipeline(data.text)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    filename = (file.filename or "").lower()
    
    text = ocr_pdf_bytes(content) if filename.endswith(".pdf") else ocr_image_bytes(content)
    # Ensure run_analysis_pipeline handles empty strings if OCR fails
    return run_analysis_pipeline(text or "")

@app.post("/chat")
async def clinical_chat(data: ChatRequest):
    user_query = data.message.lower()
    meds_on_hand = ", ".join(data.context_meds) if data.context_meds else "None detected"
    
    if "dose" in user_query:
        reply = f"For {meds_on_hand}, dosage must be checked against CrCl (Renal) and Age. WHO suggests cautious prescribing in pediatrics/geriatrics."
    elif "generic" in user_query or "alternative" in user_query:
        reply = "WHO core indicators prioritize generic prescribing to reduce healthcare costs and improve medicine availability."
    else:
        reply = f"I have reviewed the prescription ({meds_on_hand}). Do you need info on drug-drug interactions or counseling points?"

    return {"reply": reply}

# ---------------- NEW AI ENDPOINTS ---------------- #

@app.post("/api/ai/clinical-context")
async def get_clinical_context(data: dict = Body(...)):
    text = data.get("text", "")
    if not text or clinical_model is None:
        raise HTTPException(status_code=400, detail="Text missing or model not loaded")
    
    inputs = clinical_tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = clinical_model(**inputs)
    
    tensor_shape = list(outputs.last_hidden_state.shape)
    
    return {
        "model": "emilyalsentzer/Bio_ClinicalBERT",
        "tokens_processed": tensor_shape[1],
        "feature_dimensions": tensor_shape[2],
        "status": "success"
    }

@app.post("/api/ai/bio-context")
async def get_bio_context(data: dict = Body(...)):
    text = data.get("text", "")
    if not text or bio_model is None:
        raise HTTPException(status_code=400, detail="Text missing or model not loaded")
    
    inputs = bio_tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        outputs = bio_model(**inputs)
        
    tensor_shape = list(outputs.last_hidden_state.shape)
    
    return {
        "model": "dmis-lab/biobert-v1.1",
        "tokens_processed": tensor_shape[1],
        "feature_dimensions": tensor_shape[2],
        "status": "success"
    }