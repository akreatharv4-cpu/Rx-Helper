from flask import Flask, request, jsonify
import re
app = Flask(__name__)
INTERACTIONS = {("metformin","atenolol"): {"severity":"Moderate","msg":"May mask hypoglycemia symptoms"}}

def extract_info(text):
    data = {"age": None,"drugs": []}
    age_match = re.search(r'(\d+)\s*yr', text.lower())
    if age_match: data["age"] = age_match.group(1)
    for line in text.split("\n"):
        if "mg" in line.lower(): data["drugs"].append(line.strip())
    return data

@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    data = extract_info(text)
    alerts = []
    if not data["age"]: alerts.append("Missing age")
    interactions = []
    if "metformin" in str(data["drugs"]).lower() and "atenolol" in str(data["drugs"]).lower():
        interactions.append(INTERACTIONS[("metformin","atenolol")])
    return jsonify({"data":data,"alerts":alerts,"interactions":interactions,"counseling":"Monitor BP & sugar"})

if __name__ == "__main__":
    app.run(debug=True)
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rxhelper.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from .db import Base

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_filename = Column(String, nullable=True)
    source_type = Column(String, nullable=False)  # image/pdf/text
    raw_text = Column(Text, nullable=False)

    extracted_json = Column(Text, nullable=False)  # JSON string
    flags_json = Column(Text, nullable=False)      # JSON string
from pydantic import BaseModel
from typing import Any, Optional, List, Dict

class AnalyzeTextRequest(BaseModel):
    text: str
    filename: Optional[str] = None

class PrescriptionOut(BaseModel):
    id: int
    created_at: str
    source_filename: Optional[str]
    source_type: str
    raw_text: str
    extracted: Dict[str, Any]
    flags: List[Dict[str, Any]]

class WhoMetricsOut(BaseModel):
    total_prescriptions: int
    total_drugs: int
    avg_drugs_per_prescription: float
    percent_generic: float
    percent_antibiotic_prescriptions: float
    percent_injection_prescriptions: float
    percent_eml: float
    import json
from datetime import datetime

def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def loads(s: str):
    return json.loads(s)

def iso(dt) -> str:
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
    import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

def ocr_image_bytes(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # simple preprocessing hook point (could add thresholding, etc.)
    text = pytesseract.image_to_string(img)
    return text.strip()

def ocr_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=max_pages)
    out = []
    for page in pages:
        out.append(pytesseract.image_to_string(page))
    return "\n".join(out).strip()
    import re
from typing import Dict, Any, List, Optional

FREQ_PATTERNS = [
    r"\bOD\b", r"\bBD\b", r"\bTDS\b", r"\bQID\b",
    r"\bonce daily\b", r"\btwice daily\b", r"\bthrice daily\b",
    r"\bevery\s+\d+\s*(hours|hrs|h)\b",
]

ROUTE_HINTS = {
    "iv": "IV",
    "im": "IM",
    "po": "PO",
    "oral": "PO",
    "subcut": "SC",
    "sc": "SC",
    "topical": "TOP",
}

FORM_HINTS = ["tablet", "tab", "capsule", "cap", "syrup", "suspension", "inj", "injection", "cream", "ointment", "drops"]

def _clean_lines(text: str) -> List[str]:
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l and len(l) > 2]
    return lines

def _extract_patient_block(text: str) -> Dict[str, Optional[str]]:
    # Very lightweight heuristics
    name = None
    age = None
    sex = None
    weight = None
    date = None

    m = re.search(r"(?:name|patient)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if m:
        name = m.group(1).split("\n")[0].strip()

    m = re.search(r"\bage\s*[:\-]?\s*(\d{1,3})\b", text, re.IGNORECASE)
    if m:
        age = m.group(1)

    m = re.search(r"\b(sex|gender)\s*[:\-]?\s*(male|female|m|f)\b", text, re.IGNORECASE)
    if m:
        sex = m.group(2).upper()

    m = re.search(r"\bwt|weight\s*[:\-]?\s*(\d{2,3}(\.\d+)?)\s*(kg)?\b", text, re.IGNORECASE)
    if m:
        weight = m.group(1)

    m = re.search(r"\b(date)\s*[:\-]?\s*([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{2,4})\b", text, re.IGNORECASE)
    if m:
        date = m.group(2)

    return {"name": name, "age": age, "sex": sex, "weight_kg": weight, "date": date}

def _looks_like_med_line(line: str) -> bool:
    # contains dose units or form hints
    if re.search(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|units)\b", line, re.IGNORECASE):
        return True
    if any(h in line.lower() for h in FORM_HINTS):
        return True
    # Starts with Rx-like bullet/number
    if re.match(r"^(\d+[\).\s]|[-*]|rx\b)", line.lower()):
        return True
    return False

def _parse_med_line(line: str) -> Dict[str, Any]:
    original = line
    line = re.sub(r"^\s*(\d+[\).\s]+|[-*]\s+|rx[:\s]*)", "", line, flags=re.IGNORECASE).strip()

    strength = None
    m = re.search(r"(\d+(\.\d+)?)\s*(mg|mcg|g|ml|iu|units)\b", line, re.IGNORECASE)
    if m:
        strength = f"{m.group(1)} {m.group(3).lower()}"

    duration = None
    m = re.search(r"\bfor\s+(\d+)\s*(days|day|weeks|week|months|month)\b", line, re.IGNORECASE)
    if m:
        duration = f"{m.group(1)} {m.group(2).lower()}"

    freq = None
    for pat in FREQ_PATTERNS:
        m = re.search(pat, line, re.IGNORECASE)
        if m:
            freq = m.group(0)
            break

    route = None
    for k, v in ROUTE_HINTS.items():
        if re.search(rf"\b{k}\b", line, re.IGNORECASE):
            route = v
            break

    form = None
    for f in FORM_HINTS:
        if re.search(rf"\b{re.escape(f)}\b", line, re.IGNORECASE):
            form = f.lower()
            break

    # Drug name guess: take leading words until strength/form keyword
    stop_tokens = ["mg", "mcg", "g", "ml", "iu", "units"] + FORM_HINTS + ["po", "iv", "im", "sc", "od", "bd", "tds", "qid"]
    tokens = re.split(r"\s+", line)
    name_tokens = []
    for t in tokens:
        t_clean = re.sub(r"[^\w\-]", "", t).lower()
        if not t_clean:
            continue
        if t_clean in stop_tokens:
            break
        if re.match(r"^\d+(\.\d+)?$", t_clean):
            break
        name_tokens.append(t)
        if len(name_tokens) >= 5:
            break
    drug_name = " ".join(name_tokens).strip() or None

    return {
        "raw_line": original,
        "drug_name": drug_name,
        "strength": strength,
        "form": form,
        "route": route,
        "frequency": freq,
        "duration": duration,
    }

def extract_structured(text: str) -> Dict[str, Any]:
    patient = _extract_patient_block(text)
    lines = _clean_lines(text)

    meds = []
    for line in lines:
        if _looks_like_med_line(line):
            med = _parse_med_line(line)
            # avoid obvious non-meds
            if med["drug_name"] and len(med["drug_name"]) >= 2:
                meds.append(med)

    return {
        "patient": patient,
        "medications": meds,
        "meta": {
            "medication_count": len(meds),
        }
    }
    from typing import Dict, Any, List
from rapidfuzz import fuzz

# Very small demo lists (replace with real datasets)
COMMON_ANTIBIOTICS = {
    "amoxicillin", "azithromycin", "ciprofloxacin", "ceftriaxone",
    "doxycycline", "metronidazole", "cefixime", "cephalexin",
}
INJECTION_HINT_FORMS = {"inj", "injection"}
ESSENTIAL_MEDICINES_DEMO = {
    "paracetamol", "amoxicillin", "metformin", "oral rehydration salts", "ors",
    "omeprazole", "ceftriaxone", "salbutamol"
}

# DDI placeholder demo pairs (normalized lower strings)
DDI_DEMO = {
    tuple(sorted(("warfarin", "metronidazole"))): ("major", "Increased bleeding risk; monitor INR/avoid."),
    tuple(sorted(("aceclofenac", "warfarin"))): ("major", "Bleeding risk increases with NSAIDs."),
    tuple(sorted(("ibuprofen", "warfarin"))): ("major", "Bleeding risk increases with NSAIDs."),
}

def _norm_name(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(name.lower().split())

def classify_meds(extracted: Dict[str, Any]) -> Dict[str, Any]:
    meds = extracted.get("medications", [])
    for m in meds:
        n = _norm_name(m.get("drug_name"))
        m["normalized_name"] = n
        m["is_antibiotic"] = bool(n and any(fuzz.partial_ratio(n, ab) >= 90 for ab in COMMON_ANTIBIOTICS))
        m["is_injection"] = bool(
            (m.get("route") in {"IV", "IM", "SC"})
            or (m.get("form") in INJECTION_HINT_FORMS)
            or (m.get("raw_line") and "inj" in m["raw_line"].lower())
        )
        # naive "generic vs brand": if contains uppercase or ® etc. you’d do better with RxNorm
        raw = m.get("raw_line", "")
        m["is_generic_name"] = bool(m.get("drug_name") and m["drug_name"].islower())
        m["is_eml"] = bool(n and any(fuzz.partial_ratio(n, eml) >= 90 for eml in ESSENTIAL_MEDICINES_DEMO))
    return extracted

def apply_flags(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    meds = extracted.get("medications", [])
    patient = extracted.get("patient", {})

    # Missing critical info (MVP set)
    missing = []
    if not patient.get("name"): missing.append("patient.name")
    if not patient.get("age"): missing.append("patient.age")
    if len(meds) == 0: missing.append("medications")

    for idx, m in enumerate(meds):
        if not m.get("drug_name"): missing.append(f"medications[{idx}].drug_name")
        if not m.get("strength"): missing.append(f"medications[{idx}].strength")
        if not m.get("frequency"): missing.append(f"medications[{idx}].frequency")
        if not m.get("duration"): missing.append(f"medications[{idx}].duration")

    if missing:
        flags.append({"type": "missing_fields", "severity": "moderate", "details": missing})

    # Polypharmacy
    if len(meds) >= 5:
        flags.append({"type": "polypharmacy", "severity": "moderate", "details": {"med_count": len(meds)}})

    # Duplicate therapy (very naive: same normalized name repeated)
    names = [m.get("normalized_name") for m in meds if m.get("normalized_name")]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        flags.append({"type": "duplicate_therapy", "severity": "moderate", "details": {"duplicates": dupes}})

    # DDIs (demo)
    normalized = [n for n in names if n]
    ddis = []
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            pair = tuple(sorted((normalized[i], normalized[j])))
            if pair in DDI_DEMO:
                sev, msg = DDI_DEMO[pair]
                ddis.append({"pair": list(pair), "severity": sev, "message": msg})
    if ddis:
        flags.append({"type": "drug_drug_interactions", "severity": "major", "details": ddis})

    return flags
    from typing import List, Dict, Any

def compute_who(prescriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_prescriptions = len(prescriptions)
    total_drugs = 0

    generic_count = 0
    eml_count = 0

    abx_presc = 0
    inj_presc = 0

    for p in prescriptions:
        meds = p.get("extracted", {}).get("medications", [])
        total_drugs += len(meds)

        has_abx = any(m.get("is_antibiotic") for m in meds)
        has_inj = any(m.get("is_injection") for m in meds)
        if has_abx: abx_presc += 1
        if has_inj: inj_presc += 1

        generic_count += sum(1 for m in meds if m.get("is_generic_name"))
        eml_count += sum(1 for m in meds if m.get("is_eml"))

    avg_drugs = (total_drugs / total_prescriptions) if total_prescriptions else 0.0
    percent_generic = (generic_count / total_drugs * 100) if total_drugs else 0.0
    percent_eml = (eml_count / total_drugs * 100) if total_drugs else 0.0
    percent_abx = (abx_presc / total_prescriptions * 100) if total_prescriptions else 0.0
    percent_inj = (inj_presc / total_prescriptions * 100) if total_prescriptions else 0.0

    return {
        "total_prescriptions": total_prescriptions,
        "total_drugs": total_drugs,
        "avg_drugs_per_prescription": round(avg_drugs, 3),
        "percent_generic": round(percent_generic, 2),
        "percent_antibiotic_prescriptions": round(percent_abx, 2),
        "percent_injection_prescriptions": round(percent_inj, 2),
        "percent_eml": round(percent_eml, 2),
    }
    import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from .db import Base, engine, get_db
from .models import Prescription
from .schemas import AnalyzeTextRequest
from .utils import dumps, loads, iso
from .ocr import ocr_image_bytes, ocr_pdf_bytes
from .nlp import extract_structured
from .rules import classify_meds, apply_flags
from .who import compute_who

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RxHelper API", version="0.1.0")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

def analyze_text_core(text: str) -> tuple[dict, list]:
    extracted = extract_structured(text)
    extracted = classify_meds(extracted)
    flags = apply_flags(extracted)
    return extracted, flags

@app.post("/analyze_text")
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_db)):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    extracted, flags = analyze_text_core(req.text)

    p = Prescription(
        source_filename=req.filename,
        source_type="text",
        raw_text=req.text,
        extracted_json=dumps(extracted),
        flags_json=dumps(flags),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {
        "id": p.id,
        "created_at": iso(p.created_at),
        "source_filename": p.source_filename,
        "source_type": p.source_type,
        "raw_text": p.raw_text,
        "extracted": extracted,
        "flags": flags,
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    name = file.filename or "upload"
    ctype = (file.content_type or "").lower()

    if "pdf" in ctype or name.lower().endswith(".pdf"):
        text = ocr_pdf_bytes(content, max_pages=3)
        source_type = "pdf"
    else:
        text = ocr_image_bytes(content)
        source_type = "image"

    if not text.strip():
        raise HTTPException(status_code=422, detail="OCR produced empty text. Try a clearer image.")

    extracted, flags = analyze_text_core(text)

    p = Prescription(
        source_filename=name,
        source_type=source_type,
        raw_text=text,
        extracted_json=dumps(extracted),
        flags_json=dumps(flags),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {
        "id": p.id,
        "created_at": iso(p.created_at),
        "source_filename": p.source_filename,
        "source_type": p.source_type,
        "raw_text": p.raw_text,
        "extracted": extracted,
        "flags": flags,
    }

@app.get("/prescriptions")
def list_prescriptions(db: Session = Depends(get_db)):
    rows = db.query(Prescription).order_by(Prescription.id.desc()).limit(100).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "created_at": iso(r.created_at),
            "source_filename": r.source_filename,
            "source_type": r.source_type,
            "raw_text": r.raw_text,
            "extracted": loads(r.extracted_json),
            "flags": loads(r.flags_json),
        })
    return out

@app.get("/prescriptions/{pid}")
def get_prescription(pid: int, db: Session = Depends(get_db)):
    r = db.query(Prescription).filter(Prescription.id == pid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": r.id,
        "created_at": iso(r.created_at),
        "source_filename": r.source_filename,
        "source_type": r.source_type,
        "raw_text": r.raw_text,
        "extracted": loads(r.extracted_json),
        "flags": loads(r.flags_json),
    }

@app.get("/metrics/who")
def who_metrics(db: Session = Depends(get_db)):
    rows = db.query(Prescription).all()
    prescs = []
    for r in rows:
        prescs.append({
            "id": r.id,
            "extracted": loads(r.extracted_json),
        })
    return compute_who(prescs)
    from typing import List, Dict, Any

def compute_who(prescriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_prescriptions = len(prescriptions)
    total_drugs = 0

    generic_count = 0
    eml_count = 0

    abx_presc = 0
    inj_presc = 0

    for p in prescriptions:
        meds = p.get("extracted", {}).get("medications", [])
        total_drugs += len(meds)

        has_abx = any(m.get("is_antibiotic") for m in meds)
        has_inj = any(m.get("is_injection") for m in meds)
        if has_abx: abx_presc += 1
        if has_inj: inj_presc += 1

        generic_count += sum(1 for m in meds if m.get("is_generic_name"))
        eml_count += sum(1 for m in meds if m.get("is_eml"))

    avg_drugs = (total_drugs / total_prescriptions) if total_prescriptions else 0.0
    percent_generic = (generic_count / total_drugs * 100) if total_drugs else 0.0
    percent_eml = (eml_count / total_drugs * 100) if total_drugs else 0.0
    percent_abx = (abx_presc / total_prescriptions * 100) if total_prescriptions else 0.0
    percent_inj = (inj_presc / total_prescriptions * 100) if total_prescriptions else 0.0

    return {
        "total_prescriptions": total_prescriptions,
        "total_drugs": total_drugs,
        "avg_drugs_per_prescription": round(avg_drugs, 3),
        "percent_generic": round(percent_generic, 2),
        "percent_antibiotic_prescriptions": round(percent_abx, 2),
        "percent_injection_prescriptions": round(percent_inj, 2),
        "percent_eml": round(percent_eml, 2),
    }
    import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from .db import Base, engine, get_db
from .models import Prescription
from .schemas import AnalyzeTextRequest
from .utils import dumps, loads, iso
from .ocr import ocr_image_bytes, ocr_pdf_bytes
from .nlp import extract_structured
from .rules import classify_meds, apply_flags
from .who import compute_who

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RxHelper API", version="0.1.0")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

def analyze_text_core(text: str) -> tuple[dict, list]:
    extracted = extract_structured(text)
    extracted = classify_meds(extracted)
    flags = apply_flags(extracted)
    return extracted, flags

@app.post("/analyze_text")
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_db)):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    extracted, flags = analyze_text_core(req.text)

    p = Prescription(
        source_filename=req.filename,
        source_type="text",
        raw_text=req.text,
        extracted_json=dumps(extracted),
        flags_json=dumps(flags),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {
        "id": p.id,
        "created_at": iso(p.created_at),
        "source_filename": p.source_filename,
        "source_type": p.source_type,
        "raw_text": p.raw_text,
        "extracted": extracted,
        "flags": flags,
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    name = file.filename or "upload"
    ctype = (file.content_type or "").lower()

    if "pdf" in ctype or name.lower().endswith(".pdf"):
        text = ocr_pdf_bytes(content, max_pages=3)
        source_type = "pdf"
    else:
        text = ocr_image_bytes(content)
        source_type = "image"

    if not text.strip():
        raise HTTPException(status_code=422, detail="OCR produced empty text. Try a clearer image.")

    extracted, flags = analyze_text_core(text)

    p = Prescription(
        source_filename=name,
        source_type=source_type,
        raw_text=text,
        extracted_json=dumps(extracted),
        flags_json=dumps(flags),
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {
        "id": p.id,
        "created_at": iso(p.created_at),
        "source_filename": p.source_filename,
        "source_type": p.source_type,
        "raw_text": p.raw_text,
        "extracted": extracted,
        "flags": flags,
    }

@app.get("/prescriptions")
def list_prescriptions(db: Session = Depends(get_db)):
    rows = db.query(Prescription).order_by(Prescription.id.desc()).limit(100).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "created_at": iso(r.created_at),
            "source_filename": r.source_filename,
            "source_type": r.source_type,
            "raw_text": r.raw_text,
            "extracted": loads(r.extracted_json),
            "flags": loads(r.flags_json),
        })
    return out

@app.get("/prescriptions/{pid}")
def get_prescription(pid: int, db: Session = Depends(get_db)):
    r = db.query(Prescription).filter(Prescription.id == pid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": r.id,
        "created_at": iso(r.created_at),
        "source_filename": r.source_filename,
        "source_type": r.source_type,
        "raw_text": r.raw_text,
        "extracted": loads(r.extracted_json),
        "flags": loads(r.flags_json),
    }

@app.get("/metrics/who")
def who_metrics(db: Session = Depends(get_db)):
    rows = db.query(Prescription).all()
    prescs = []
    for r in rows:
        prescs.append({
            "id": r.id,
            "extracted": loads(r.extracted_json),
        })
    return compute_who(prescs)
