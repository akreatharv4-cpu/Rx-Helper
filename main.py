from flask import Flask, request, jsonify, render_template
import re
import pytesseract
from PIL import Image

app = Flask(__name__)

# Example interaction database
INTERACTIONS = {
    ("metformin", "atenolol"): {
        "severity": "Moderate",
        "msg": "May mask hypoglycemia symptoms"
    },
    ("warfarin", "aspirin"): {
        "severity": "High",
        "msg": "High risk of bleeding"
    }
}


def extract_info(text):

    data = {"age": None, "drugs": []}

    text = text.lower()

    # Extract age
    age_match = re.search(r'(\d+)\s*yr', text)
    if age_match:
        data["age"] = age_match.group(1)

    # Extract drugs
    for line in text.split("\n"):
        if "mg" in line or "tablet" in line or "tab" in line:
            data["drugs"].append(line.strip())

    return data


def analyze_drugs(drug_list):

    alerts = []
    interactions = []
    risk = "safe"

    drug_text = str(drug_list).lower()

    # Check interactions
    for (d1, d2), info in INTERACTIONS.items():

        if d1 in drug_text and d2 in drug_text:
            interactions.append(info)

            if info["severity"] == "Moderate":
                risk = "moderate"

            if info["severity"] == "High":
                risk = "high"

    return alerts, interactions, risk


@app.route("/")
def home():
    return render_template("index.html")


# Manual prescription text analysis
@app.route("/analyze", methods=["POST"])
def analyze():

    data_req = request.get_json(silent=True) or {}
    text = data_req.get("text", "")

    data = extract_info(text)

    alerts, interactions, risk = analyze_drugs(data["drugs"])

    if not data["age"]:
        alerts.append("Missing patient age")

    return jsonify({
        "data": data,
        "alerts": alerts,
        "interactions": interactions,
        "risk": risk
    })


# Image prescription upload
@app.route("/upload", methods=["POST"])
def upload():

    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file uploaded"})

    image = Image.open(file)

    text = pytesseract.image_to_string(image)

    data = extract_info(text)

    alerts, interactions, risk = analyze_drugs(data["drugs"])

    return jsonify({
        "extracted_text": text,
        "data": data,
        "alerts": alerts,
        "interactions": interactions,
        "risk": risk
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
