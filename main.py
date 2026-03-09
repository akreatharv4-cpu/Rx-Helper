from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pandas as pd
import json
import re
from rapidfuzz import process, fuzz
from typing import List

from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI(title="Rx-Helper Clinical Assistant")

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

# ---------------- LOAD DATABASE FILES ----------------

def load_csv(path):
    try:
        return pd.read_csv(path)
    except:
        print(f"⚠ Missing file: {path}")
        return pd.DataFrame()


df_meds = load_csv("medicines.csv")
interactions_df = load_csv("drug_interactions.csv")
dosage_df = load_csv("dosage_reference.csv")
classes_df = load_csv("drug_classes.csv")

# shorthand dictionary
try:
    with open("abbreviations.json") as f:
        ABBR = json.load(f)
except:
    ABBR = {}

# ---------------- PREPARE MEDICINE LIST ----------------

if not df_meds.empty:
    med_names = df_meds.iloc[:,0].dropna().astype(str).str.lower().tolist()
else:
    med_names = []

# dosage lookup
dosage_lookup = {}
if not dosage_df.empty:
    for _,row in dosage_df.iterrows():
        dosage_lookup[row["drug"].lower()] = row["max_daily_mg"]

# class lookup
class_lookup = {}
if not classes_df.empty:
    for _,row in classes_df.iterrows():
        class_lookup[row["drug"].lower()] = row["class"]

# ---------------- DOSAGE FORM WORDS ----------------

FORM_WORDS = [
    "tab","tablet","tabs",
    "cap","capsule","caps",
    "inj","injection",
    "syp","syrup",
    "susp","suspension",
    "cream","ointment",
    "drops","drop",
    "inhaler"
]

# ---------------- TEXT CLEANING ----------------

def expand_abbreviations(text):

    for k,v in ABBR.items():
        text = re.sub(rf"\b{k}\b", v, text, flags=re.IGNORECASE)

    return text


# ---------------- CLEAN OCR TEXT ----------------

def clean_text(text):

    text = text.lower()

    tokens = text.split()

    filtered = []

    for t in tokens:
        if t in FORM_WORDS:
            continue
        filtered.append(t)

    return " ".join(filtered)


# ---------------- MEDICINE DETECTION ----------------

def detect_medicines(text:str)->List[str]:

    detected=set()

    text = clean_text(text)

    tokens=text.split()

    for token in tokens:

        match=process.extractOne(
            token,
            med_names,
            scorer=fuzz.token_set_ratio
        )

        if match and match[1]>85:
            detected.add(match[0])

    return list(detected)


# ---------------- DOSE EXTRACTION ----------------

def extract_doses(text):

    doses={}

    matches=re.findall(r"(\w+)\s*(\d+)\s*mg",text.lower())

    for drug,dose in matches:

        match=process.extractOne(
            drug,
            med_names,
            scorer=fuzz.token_set_ratio
        )

        if match and match[1]>80:
            doses[match[0]]=int(dose)

    return doses


# ---------------- DOSE VALIDATION ----------------

def check_dosage(doses):

    warnings=[]

    for drug,dose in doses.items():

        if drug in dosage_lookup:

            if dose>dosage_lookup[drug]:

                warnings.append({
                    "drug":drug,
                    "dose":dose,
                    "limit":dosage_lookup[drug],
                    "warning":"Dose exceeds recommended maximum"
                })

    return warnings


# ---------------- DRUG CLASS ----------------

def get_drug_classes(meds):

    result={}

    for m in meds:
        result[m]=class_lookup.get(m,"Unknown")

    return result


# ---------------- INTERACTION CHECK ----------------

def check_interactions(meds):

    alerts=[]

    if interactions_df.empty:
        return alerts

    interactions_df["drug1"]=interactions_df["drug1"].str.lower()
    interactions_df["drug2"]=interactions_df["drug2"].str.lower()

    for i in range(len(meds)):
        for j in range(i+1,len(meds)):

            d1=meds[i]
            d2=meds[j]

            result=interactions_df[
                ((interactions_df["drug1"]==d1)&(interactions_df["drug2"]==d2))|
                ((interactions_df["drug1"]==d2)&(interactions_df["drug2"]==d1))
            ]

            if not result.empty:

                row=result.iloc[0]

                severity=row.get("severity","Moderate")

                alerts.append({
                    "drug1":d1,
                    "drug2":d2,
                    "severity":severity,
                    "message":row.get("message","Interaction detected")
                })

    return alerts


# ---------------- OCR API ----------------

@app.post("/upload")
async def upload_file(file:UploadFile=File(...)):

    try:

        content=await file.read()

        if file.filename.lower().endswith(".pdf"):
            text=ocr_pdf_bytes(content)
        else:
            text=ocr_image_bytes(content)

    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

    # shorthand expansion
    text=expand_abbreviations(text)

    medicines=detect_medicines(text)

    interactions=check_interactions(medicines)

    doses=extract_doses(text)

    dose_warnings=check_dosage(doses)

    drug_classes=get_drug_classes(medicines)

    return{
        "medicines_detected":medicines,
        "drug_classes":drug_classes,
        "drug_interactions":interactions,
        "dose_warnings":dose_warnings,
        "raw_text":text
    }


# ---------------- INDEX PAGE ----------------

@app.get("/",response_class=HTMLResponse)
async def index(request:Request):

    return templates.TemplateResponse(
        "index.html",
        {"request":request}
    )
