from flask import Flask, request, jsonify
import re

app = Flask(__name__)

INTERACTIONS = {
    ("metformin","atenolol"): {
        "severity":"Moderate",
        "msg":"May mask hypoglycemia symptoms"
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

@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")

    data = extract_info(text)

    alerts = []
    if not data["age"]:
        alerts.append("Missing age")

    interactions = []

    if "metformin" in str(data["drugs"]).lower() and "atenolol" in str(data["drugs"]).lower():
        interactions.append(INTERACTIONS[("metformin","atenolol")])

    return jsonify({
        "data": data,
        "alerts": alerts,
        "interactions": interactions,
        "counseling": "Monitor BP & sugar"
    })

if __name__ == "__main__":
    app.run()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder=".")

@app.route("/")
def home():
    return send_from_directory(".", "index.html")
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")
