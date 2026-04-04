# ---------------- ROUTES ----------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test")
async def test():
    return {"status": "working"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        # Check OCR availability
        if ocr_image_bytes is None or ocr_pdf_bytes is None:
            raise Exception("OCR functions not loaded")

        content = await file.read()
        filename = (file.filename or "").lower()

        print("📁 FILE RECEIVED:", filename)

        # OCR processing
        if filename.endswith(".pdf"):
            text = ocr_pdf_bytes(content)
            source_type = "pdf"
        else:
            text = ocr_image_bytes(content)
            source_type = "image"

        if not text or len(text.strip()) == 0:
            raise Exception("OCR returned empty text")

        print("🧾 OCR TEXT:", text[:200])

        # Medicine detection
        meds = detect_medicines(text)
        print("💊 MEDS:", meds)

        # Interaction check
        interactions = check_interactions(meds)
        print("⚠ INTERACTIONS:", interactions)

        return {
            "success": True,
            "source_type": source_type,
            "medicines_detected": meds,
            "interactions": interactions,
            "raw_text": text,
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))