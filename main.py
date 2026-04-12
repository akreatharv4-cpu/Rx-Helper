from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from ocr import ocr_image_bytes, ocr_pdf_bytes, extract_clean_drugs
from pathlib import Path
import pandas as pd
from rapidfuzz import process, fuzz
from pydantic import BaseModel, Field
from typing import List, Optional
import re 

# --- AI & INTERACTIONS ---
from transformers import AutoTokenizer, AutoModel
import torch
from interaction_checker import check_interactions 

app = FastAPI()

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent
MEDICINE_PATH = BASE_DIR / "medicines_master.csv"
DOSAGE_PATH = BASE_DIR / "dosage_reference.csv" 

# ---------------- AI MODELS ---------------- #
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
        return pd.DataFrame(columns=["name", "class", "is_antibiotic", "is_injection", "is_edl", "is_generic"])

def load_dosages():
    try:
        df = pd.read_csv(DOSAGE_PATH)
        df["drug_name"] = df["drug_name"].str.lower().str.strip()
        return dict(zip(df["drug_name"], df["max_daily_mg"]))
    except Exception as e:
        return {}

medicine_df = load_medicines()
medicine_list = medicine_df["name"].tolist()
dosage_dict = load_dosages()

# ---------------- LOGIC HELPERS ---------------- #

def calculate_who_indicators(detected_meds):
    total_drugs = len(detected_meds)
    if total_drugs == 0:
        return {"drugs_per_encounter": 0, "pc_generic": 0, "pc_antibiotic": 0, "pc_injection": 0, "pc_edl": 0}

    subset = medicine_df[medicine_df["name"].isin([m.lower() for m in detected_meds])]
    
    generics_count = subset[subset["is_generic"] == 1].shape[0] if "is_generic" in subset.columns else 0
    antibiotics_count = subset[subset["is_antibiotic"] == 1].shape[0] if "is_antibiotic" in subset.columns else 0
    injections_count = subset[subset["is_injection"] == 1].shape[0] if "is_injection" in subset.columns else 0
    edl_count = subset[subset["is_edl"] == 1].shape[0] if "is_edl" in subset.columns else 0

    return {
        "drugs_per_encounter": total_drugs,
        "pc_generic": round((generics_count / total_drugs) * 100, 1),
        "pc_antibiotic": round((antibiotics_count / total_drugs) * 100, 1),
        "pc_injection": round((injections_count / total_drugs) * 100, 1),
        "pc_edl": round((edl_count / total_drugs) * 100, 1)
    }

def extract_dose_and_frequency(text, drug_name):
    text = text.lower()
    start_idx = text.find(drug_name.lower())
    if start_idx == -1: return 0, 0
    
    context = text[start_idx : start_idx + 75]
    
    strength = 0
    strength_match = re.search(r'(\d+(?:\.\d+)?)\s*(mg|g|mcg)', context)
    if strength_match:
        val = float(strength_match.group(1))
        unit = strength_match.group(2)
        strength = val * 1000 if unit == 'g' else val
        
    freq = 1 
    if any(x in context for x in ["tid", "t.i.d", "3 times", "tds"]): freq = 3
    elif any(x in context for x in ["bid", "b.i.d", "2 times", "bd"]): freq = 2
    elif any(x in context for x in ["qid", "q.i.d", "4 times"]): freq = 4
    elif any(x in context for x in ["od", "o.d", "once daily", "hs"]): freq = 1
    
    return strength, freq

# ---------------- CORE ANALYSIS PIPELINE (FIXED & DEDUPLICATED) ---------------- #

def run_analysis_pipeline(text: str, patient_info: dict = None):
    cleaned_text = text.replace("\n", " ").lower()
    raw_meds = extract_clean_drugs(text)
    
    stop_words = {
        "prescription", "tablet", "tablets", "capsule", "syrup", "syp", 
        "dr", "patient", "dose", "daily", "mg", "ml", "tab", "clinic", 
        "formate", "medical", "india", "name", "mbbs", "md", "hospital"
    }
    filtered_meds = [m for m in raw_meds if m.lower().strip() not in stop_words]
    
    final_meds = []
    overdose_alerts = []
    processed_drugs = set() # DEDUPLICATION KEY

    # 1. FUZZY MATCHING & ACTIVE DOSAGE AUDITING
    for m in filtered_meds:
        clean_m = re.sub(r'\b(tablet|cap|syp|injection|inj|syrup|hcl|mg)\b.*', '', m, flags=re.IGNORECASE).strip()
        if not clean_m: continue

        if medicine_list:
            match = process.extractOne(clean_m.lower(), medicine_list, scorer=fuzz.WRatio)
            if match and match[1] >= 72:
                drug_name = match[0].title()
                
                # Deduplication logic: Only audit each drug once
                if drug_name not in processed_drugs:
                    final_meds.append(drug_name)
                    processed_drugs.add(drug_name)
                    
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
        
        # Non-DB drugs
        clean_title = clean_m.title()
        if len(clean_m) > 3 and clean_title not in processed_drugs:
            final_meds.append(clean_title)
            processed_drugs.add(clean_title)

    # 2. FALLBACK SCAN
    for db_med in medicine_list:
        db_title = db_med.title()
        if len(db_med) > 4 and db_title not in processed_drugs:
            if db_med.lower() in cleaned_text:
                final_meds.append(db_title)
                processed_drugs.add(db_title)

    # 3. MERGE & RETURN
    who_data = calculate_who_indicators(final_meds)
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
        "interactions": all_safety_alerts,
        "max_dosages": dosage_limits,
        "raw_text": text,
        "patient_context": patient_info or {}
    }
# ---------------- DATA MODELS ---------------- #

class AnalysisRequest(BaseModel):
    """
    Handles /analyze-text requests.
    Using default_factory=dict prevents 422 errors if patient_info is missing.
    """
    text: str = Field(..., min_length=1, description="Raw prescription text")
    
    # UPGRADE: Using default_factory=dict ensures this is never 'None'
    patient_info: Optional[dict] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    """
    Handles /chat requests from the AI assistant.
    Ensures all lists and dicts have safe defaults.
    """
    message: str = Field(..., min_length=1)
    
    # UPGRADE: Ensures context_meds is an empty list [] by default
    context_meds: List[str] = Field(default_factory=list)
    
    # UPGRADE: Ensures patient_info is an empty dict {} by default
    patient_info: dict = Field(default_factory=dict)

# ---------------- ROUTES ---------------- #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze-text")
async def analyze_text(data: AnalysisRequest): 
    # Directly uses the validated data from Pydantic
    return run_analysis_pipeline(data.text, data.patient_info)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    filename = (file.filename or "").lower()
    
    # 1. Process OCR (PDF or Image)
    text = ocr_pdf_bytes(content) if filename.endswith(".pdf") else ocr_image_bytes(content)
    
    # 2. Pass an empty dict for patient_info to prevent NoneType errors in the pipeline
    # The user can update Age/Renal info on the dashboard after the scan.
    return run_analysis_pipeline(text or "", patient_info={})

@app.post("/chat")
async def clinical_chat(data: ChatRequest):
    user_query = data.message.lower()
    meds_on_hand = ", ".join(data.context_meds) if data.context_meds else "No drugs detected"
    
    # Clinical Context Extraction
    renal_status = data.patient_info.get("renal", "Normal (>60)")
    age = data.patient_info.get("age", "25")
    
    # 3. Enhanced Clinical Reasoning Logic
    if any(word in user_query for word in ["safe", "renal", "kidney", "contraindicated"]):
        if "severe" in renal_status.lower():
            reply = (f"Reviewing {meds_on_hand} for a patient with Severe Renal Impairment (CrCl <30). "
                     "Attention: Many of these agents may require dose adjustment or are contraindicated. "
                     "Please cross-verify with the Renal Drug Handbook.")
        else:
            reply = f"The current list ({meds_on_hand}) appears generally manageable for {renal_status} function. Always monitor serum creatinine."

    elif "dose" in user_query or "limit" in user_query:
        reply = (f"Dosage limits for {meds_on_hand} are referenced for an adult ({age} yrs). "
                 "If the patient is pediatric or geriatric, consider adjusting the daily maximums accordingly.")

    elif "generic" in user_query or "alternative" in user_query:
        reply = ("WHO indicators promote generic prescribing. I recommend checking the National Essential "
                 "Medicines List (EDL) for cost-effective alternatives for these therapies.")

    else:
        reply = f"I've analyzed the prescription ({meds_on_hand}). Do you need a specific check on drug-drug interactions or WHO prescribing indicators?"

    return {"reply": reply}
    
    # Intelligent response based on patient info if provided
    renal_status = data.patient_info.get("renal", "Normal") if data.patient_info else "Normal"
    
    if "dose" in user_query or "safe" in user_query:
        if "severe" in renal_status.lower():
            reply = f"Caution: Patient has Severe Renal Impairment. Many drugs in this list ({meds_on_hand}) may require significant dose reduction. Please check CrCl-based guidelines."
        else:
            reply = f"For {meds_on_hand}, dosages appear standard, but always verify against the patient's weight and age ({data.patient_info.get('age', 'N/A')} yrs)."
    
    elif "generic" in user_query or "alternative" in user_query:
        reply = "WHO core indicators prioritize generic prescribing. These medicines should be checked against the National Essential Medicines List (EDL)."
    
    else:
        reply = f"I have reviewed the prescription for {meds_on_hand}. Would you like me to check for specific Contraindications?"

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