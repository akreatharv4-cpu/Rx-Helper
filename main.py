from flask import Flask, request, jsonify, render_template
import re

app = Flask(__name__)

# Example drug interaction database
INTERACTIONS = {
    ("metformin", "atenolol"): {
        "severity": "Moderate",
        "msg": "May mask hypoglycemia symptoms"
    }
}

def extract_info(text):
    data = {"age": None, "drugs": []}

    age_match = re.search(r'(\d+)\s*yr', text.lower())
    if age_match:
        data["age"] = age_match.group(1)

    for line in text.split("\n"):
        if "mg" in line.lower():
            data["drugs"].append(line.strip())

    return data


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    text = request.json.get("text", "")
    data = extract_info(text)

    alerts = []
    interactions = []

    if not data["age"]:
        alerts.append("Missing patient age")

    drug_text = str(data["drugs"]).lower()

    if "metformin" in drug_text and "atenolol" in drug_text:
        interactions.append(INTERACTIONS[("metformin", "atenolol")])

    return jsonify({
        "data": data,
        "alerts": alerts,
        "interactions": interactions,
        "counseling": "Monitor BP and blood glucose"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
