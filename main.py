# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pandas as pd
import io
from rapidfuzz import process, fuzz
from typing import List

# Local OCR utilities (provided in your repo)
from ocr import ocr_image_bytes, ocr_pdf_bytes

app = FastAPI(title="Rx-Helper OCR API")

# CORS (allow all for dev; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# load medicines list (one column with name)
MEDICINES_CSV = "medicines.csv"
try:
    df_meds = pd.read_csv(MEDICINES_CSV, encoding="utf-8")
    # try common column names
    if "name" in df_meds.columns:
        med_names = df_meds["name"].dropna().astype(str).str.lower().tolist()
    elif "medicine" in df_meds.columns:
        med_names = df_meds["medicine"].dropna().astype(str).str.lower().tolist()
    else:
        # fallback: take first column
        med_names = df_meds.iloc[:, 0].dropna().astype(str).str.lower().tolist()
except FileNotFoundError:
    med_names = []
    print(f"Warning: {MEDICINES_CSV} not found. Medicine matching will be disabled.")


def detect_medicines_from_text(text: str, limit: int = 50, score_cutoff: int = 70) -> List[dict]:
    """
    Use rapidfuzz to fuzzy match tokens/phrases in recognized text against med_names.
    Returns list of dicts: {"name":..., "score":..., "match":...}
    """
    results = []
    if not med_names or not text:
        return results

    # naive approach: split text into tokens and n-grams to search
    tokens = [t for t in (text.replace("\n", " ").split(" ")) if t.strip()]
    # also include sliding ngrams
    ngrams = []
    max_ngram = 4
    for i in range(len(tokens)):
        for n in range(1, max_ngram + 1):
            if i + n <= len(tokens):
                ngrams.append(" ".join(tokens[i:i + n]))

    candidates = list(dict.fromkeys(ngrams))  # unique, preserve order

    # perform fuzzy extract against medicine list
    for c in candidates:
        match, score, _ = process.extractOne(
            c.lower(), med_names, scorer=fuzz.WRatio
        ) or (None, 0, None)
        if match and score >= score_cutoff:
            results.append({"detected_text": c, "matched_name": match, "score": int(score)})

            # avoid duplicate matches for same medicine
            if len(results) >= limit:
                break

    # dedupe by matched_name keeping highest score
    final = {}
    for r in results:
        m = r["matched_name"]
        if m not in final or r["score"] > final[m]["score"]:
            final[m] = r
    return list(final.values())


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept image or PDF and return OCR text + detected medicines"""
    content = await file.read()
    content_type = file.content_type.lower()

    text = ""
    try:
        if "pdf" in content_type or file.filename.lower().endswith(".pdf"):
            text = ocr_pdf_bytes(content)
        else:
            text = ocr_image_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    detected = detect_medicines_from_text(text)

    return {
        "filename": file.filename,
        "ocr_text_snippet": text[:200],
        "detected_medicines": detected,
        "full_text": text
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    html = """
    <html>
      <head><title>Rx-Helper OCR</title></head>
      <body>
        <h2>Rx-Helper OCR service</h2>
        <p>POST an image/pdf to <code>/upload</code> to extract medicines.</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
