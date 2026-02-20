from flask import Flask, request, jsonify
import re
app = Flask(__name__)
INTERACTIONS = {("metformin","atenolol"): {"severity":"Moderate","msg":"May mask hypoglycemia symptoms"}}

def extract_info(text):
    data = {"age": None,"drugs": []}
    age_match = re.search(r'(\d+)\s*yr', text.lower())
    if age_match: data["age"] = age_match.group(1)
    for line in text.split("\n"):
        if "mg" in line.lower(): data["drugs"].append(line.strip())
    return data

@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    data = extract_info(text)
    alerts = []
    if not data["age"]: alerts.append("Missing age")
    interactions = []
    if "metformin" in str(data["drugs"]).lower() and "atenolol" in str(data["drugs"]).lower():
        interactions.append(INTERACTIONS[("metformin","atenolol")])
    return jsonify({"data":data,"alerts":alerts,"interactions":interactions,"counseling":"Monitor BP & sugar"})

if __name__ == "__main__":
    app.run(debug=True)
