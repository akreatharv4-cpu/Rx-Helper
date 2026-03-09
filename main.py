from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import easyocr
from PIL import Image
import pandas as pd
import io
import cv2
import numpy as np
import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from rapidfuzz import process
from pdf2image import convert_from_bytes

app = FastAPI()

# --- HEALTH CHECK FOR RENDER ---
@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

# --- INITIALIZE EASYOCR ---
reader = easyocr.Reader(['en'], gpu=False)

# --- STATIC + TEMPLATES ---
# Ensure directories exist to avoid errors
if not os.path.exists("static"): os.makedirs("static")
if not os.path.exists("templates"): os.makedirs("templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOAD DATASETS ---
try:
    interactions = pd.read_csv("drug_interactions.csv")
    interactions["drug1"] = interactions["drug1"].str.lower()
    interactions["drug2"] = interactions["drug2"].str.lower()
except:
    interactions = pd.DataFrame(columns=["drug1", "drug2", "severity", "message"])

try:
    medicines = pd.read_csv("medicines.csv")
    medicine_list = medicines["medicine_name"].str.lower().tolist()
except:
    medicine_list = []

# --- OCR & ANALYSIS LOGIC (Your original code continues below) ---
def preprocess_image(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return thresh

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text

def find_medicines(text):
    detected = []
    words = text.split()
    for word in words:
        if len(word) < 4: continue
        match = process.extractOne(word, medicine_list, score_cutoff=80)
        if match: detected.append(match[0])
    return list(set(detected))

def extract_doses(text):
    return re.findall(r'\d+\s?(?:mg|mcg|g|ml|units)', text)

frequency_map = {"od": "once daily", "bd": "twice daily", "tds": "three times daily", "qid": "four times daily", "sos": "as needed"}

def detect_frequency(text):
    return [val for key, val in frequency_map.items() if key in text]

def run_ocr(image):
    image = image.resize((1500, 1500))
    processed = preprocess_image(image)
    results = reader.readtext(processed)
    return " ".join([res[1] for res in results])

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def analyze_prescription(file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        pages = convert_from_bytes(contents, dpi=300)
        full_text = ""
        for page in pages[:3]:
            full_text += run_ocr(page) + "\n"
    else:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        full_text = run_ocr(image)
    
    text = clean_text(full_text)
    detected_medicines = find_medicines(text)
    
    interaction_results = []
    for i in range(len(detected_medicines)):
        for j in range(i + 1, len(detected_medicines)):
            d1, d2 = detected_medicines[i], detected_medicines[j]
            match = interactions[((interactions["drug1"] == d1) & (interactions["drug2"] == d2)) | ((interactions["drug1"] == d2) & (interactions["drug2"] == d1))]
            if not match.empty:
                row = match.iloc[0]
                interaction_results.append({"drug1": d1, "drug2": d2, "severity": row["severity"], "message": row["message"]})

    return {
        "extracted_text": text,
        "medicines_detected": detected_medicines,
        "doses_detected": extract_doses(text),
        "frequency_detected": detect_frequency(text),
        "drug_interactions": interaction_results,
        "dashboard": {"total_medicines": len(detected_medicines), "polypharmacy": len(detected_medicines) >= 5}
    }

@app.post("/report")
def generate_report(data: dict):
    file_name = "clinical_report.pdf"
    c = canvas.Canvas(file_name, pagesize=letter)
    c.drawString(50, 750, "Rx Helper Clinical Report")
    y = 710
    for m in data.get("medicines", []):
        c.drawString(60, y, m)
        y -= 20
    c.save()
    return FileResponse(file_name)
