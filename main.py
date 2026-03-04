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
