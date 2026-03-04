import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from db import Base, engine, get_db
from models import Prescription
from schemas import AnalyzeTextRequest
from utils import dumps, loads, iso
from ocr import ocr_image_bytes, ocr_pdf_bytes
from nlp import extract_structured
from rules import classify_meds, apply_flags
from who import compute_who

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RxHelper API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}
