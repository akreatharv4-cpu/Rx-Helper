from flask import Flask, request, jsonify, render_template
import re
import pandas as pd
import pytesseract
from PIL import Image
import io
from ocr_medicine_detector import detect_medicines

# Render Linux tesseract path
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)

# ================= LOAD DATABASE =================

try:
    interactions_df = pd.read_csv("drug_interactions.csv")
    interactions_df["drug1"] = interactions_df["drug1"].str.lower()
    interactions_df["drug2"] = interactions_df["drug2"].str.lower()
except Exception:
    interactions_df = pd.DataFrame(columns=["drug1","drug2","severity","message"])

# ================= ESSENTIAL DRUG LIST =================

EDL = [
    "paracetamol","amoxicillin","metformin","insulin",
    "atorvastatin","aspirin","warfarin"
]

# ================= ATC CLASSIFICATION =================

ATC_CLASSES = {
    "amoxicillin":"Antibiotic",
    "azithromycin":"Antibiotic",
    "ciprofloxacin":"Antibiotic",
    "ceftriaxone":"Antibiotic",
    "metformin":"Antidiabetic",
    "insulin":"Antidiabetic",
    "atorvastatin":"Cardiovascular",
    "warfarin":"Anticoagulant",
    "aspirin":"Antiplatelet",
    "paracetamol":"Analgesic"
}

# ================= EXTRACT PRESCRIPTION INFO =================

def extract_info(text):

    data = {"age": None, "drugs": []}

    text = text.lower()

    age_match = re.search(r'(\d+)\s*yr', text)

    if age_match:
        data["age"] = age_match.group(1)

    for line in text.split("\n"):

        if "mg" in line or "tablet" in line or "tab" in line:
            data["drugs"].append(line.strip())

    return data


# ================= DRUG INTERACTION CHECK =================

def check_interactions(drugs):

    found = []
    risk = "safe"

    for i in range(len(drugs)):
        for j in range(i+1, len(drugs)):

            d1 = drugs[i].split()[0].lower()
            d2 = drugs[j].split()[0].lower()

            match = interactions_df[
                ((interactions_df.drug1 == d1) & (interactions_df.drug2 == d2)) |
                ((interactions_df.drug1 == d2) & (interactions_df.drug2 == d1))
            ]

            if not match.empty:

                row = match.iloc[0]

                found.append({
                    "drug1": d1,
                    "drug2": d2,
                    "severity": row["severity"],
                    "message": row["message"]
                })

                if row["severity"] == "high":
                    risk = "high"
                elif row["severity"] == "moderate" and risk != "high":
                    risk = "moderate"

    return found, risk


# ================= SAFETY SCORE =================

def safety_score(drugs, interactions):

    score = 100

    score -= len(drugs) * 5

    for i in interactions:

        if i["severity"] == "moderate":
            score -= 15

        if i["severity"] == "high":
            score -= 30

    return max(score, 0)


# ================= HOME PAGE =================

@app.route("/")
def home():
    return render_template("index.html")


# ================= MANUAL TEXT ANALYSIS =================

@app.route("/analyze", methods=["POST"])
def analyze():

    data_req = request.get_json(silent=True) or {}

    text = data_req.get("text", "")

    data = extract_info(text)

    interactions, interaction_risk = check_interactions(data["drugs"])

    score = safety_score(data["drugs"], interactions)

    return jsonify({
        "drugs": data["drugs"],
        "interactions": interactions,
        "safety_score": score
    })


# ================= OCR PRESCRIPTION UPLOAD =================

@app.route("/upload", methods=["POST"])
def upload():

    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:

        image = Image.open(file.stream)

        text = pytesseract.image_to_string(image)

        file.stream.seek(0)

        detected_medicines, _ = detect_medicines(file)

        data = extract_info(text)

        interactions, interaction_risk = check_interactions(data["drugs"])

        score = safety_score(data["drugs"], interactions)

        return jsonify({
            "extracted_text": text,
            "detected_medicines": detected_medicines,
            "drug_lines": data["drugs"],
            "interactions": interactions,
            "safety_score": score
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
