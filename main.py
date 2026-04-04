from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import Base, engine
from models import Prescription
from bert_module.extractor import extract_clean_drugs
from utils.interaction_checker import check_interactions

# ---------------- APP ----------------
app = FastAPI(title="Rx-Helper Clinical Assistant")
BASE_DIR = Path(__file__).resolve().parent

# Create tables
Base.metadata.create_all(bind=engine)

# ---------------- TEMPLATES ----------------
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---------------- OCR ----------------
try:
    from ocr import ocr_image_bytes, ocr_pdf_bytes
except Exception as e:
    print(f"⚠ OCR import failed: {e}")
    ocr_image_bytes = None
    ocr_pdf_bytes = None

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC ----------------
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def detect_medicines(text):
    try:
        meds = extract_clean_drugs(text or "")
        return list(dict.fromkeys([m.upper().strip() for m in meds if m and str(m).strip()]))
    except Exception as e:
        print(f"Medicine detection error: {e}")
        return []


# ---------------- ROUTES ----------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test")
async def test():
    return {"status": "working"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if ocr_image_bytes is None or ocr_pdf_bytes is None:
        raise HTTPException(status_code=500, detail="OCR not working")

    content = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".pdf"):
            text = ocr_pdf_bytes(content)
            source_type = "pdf"
        else:
            text = ocr_image_bytes(content)
            source_type = "image"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    meds = detect_medicines(text)
    interactions = check_interactions(meds)

    return {
        "source_type": source_type,
        "medicines_detected": meds,
        "interactions": interactions,
        "raw_text": text,
    }