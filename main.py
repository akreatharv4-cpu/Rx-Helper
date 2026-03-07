from flask import Flask, request, jsonify, render_template
import re
import pandas as pd
import pytesseract
from PIL import Image
import requests

app = Flask(__name__)

# Load drug interaction database
interactions_df = pd.read_csv("drug_interactions.csv")

# Essential Drug List (simplified example)
EDL = [
"paracetamol","amoxicillin","metformin","insulin",
"atorvastatin","aspirin","warfarin"
]

# ATC classification example
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


# ---------------------------
# Extract prescription info
# ---------------------------
def extract_info(text):

    data={"age":None,"drugs":[]}

    text=text.lower()

    age_match=re.search(r'(\d+)\s*yr',text)

    if age_match:
        data["age"]=age_match.group(1)

    for line in text.split("\n"):

        if "mg" in line or "tablet" in line or "tab" in line:
            data["drugs"].append(line.strip())

    return data


# ---------------------------
# Drug interaction check
# ---------------------------
def check_interactions(drugs):

    found=[]
    risk="safe"

    for i in range(len(drugs)):
        for j in range(i+1,len(drugs)):

            d1=drugs[i].split()[0]
            d2=drugs[j].split()[0]

            match=interactions_df[
                ((interactions_df.drug1==d1)&(interactions_df.drug2==d2))|
                ((interactions_df.drug1==d2)&(interactions_df.drug2==d1))
            ]

            if not match.empty:

                row=match.iloc[0]

                found.append({
                "severity":row["severity"],
                "msg":row["message"]
                })

                if row["severity"]=="high":
                    risk="high"
                elif row["severity"]=="moderate" and risk!="high":
                    risk="moderate"

    return found,risk


# ---------------------------
# Polypharmacy risk
# ---------------------------
def polypharmacy_risk(drugs):

    count=len(drugs)

    if count>=8:
        return "high"

    if count>=5:
        return "moderate"

    return "safe"


# ---------------------------
# ADR risk
# ---------------------------
def adr_risk(age,drugs,interactions):

    score=0

    if age and int(age)>=65:
        score+=2

    if len(drugs)>=5:
        score+=2

    for i in interactions:
        if i["severity"]=="high":
            score+=3

    if score>=5:
        return "high"
    elif score>=3:
        return "moderate"
    else:
        return "low"


# ---------------------------
# EDL validation
# ---------------------------
def edl_check(drugs):

    edl_count=0

    for d in drugs:

        name=d.split()[0]

        if name in EDL:
            edl_count+=1

    percent=(edl_count/len(drugs))*100 if drugs else 0

    return percent


# ---------------------------
# WHO prescribing indicators
# ---------------------------
def who_indicators(drugs):

    antibiotics=["amoxicillin","azithromycin","ciprofloxacin","ceftriaxone"]
    injections=["ceftriaxone","insulin"]

    antibiotic_count=0
    injection_count=0

    for d in drugs:

        name=d.split()[0]

        if name in antibiotics:
            antibiotic_count+=1

        if name in injections:
            injection_count+=1

    total=len(drugs)

    indicators={
    "avg_drugs":total,
    "antibiotic_percent":(antibiotic_count/total)*100 if total else 0,
    "injection_percent":(injection_count/total)*100 if total else 0
    }

    return indicators


# ---------------------------
# Dose error detection
# ---------------------------
DOSE_RULES={
"paracetamol":4000,
"metformin":2000,
"aspirin":325
}

def dose_error(drugs):

    warnings=[]

    for d in drugs:

        name=d.split()[0]

        match=re.search(r'(\d+)\s*mg',d)

        if match and name in DOSE_RULES:

            dose=int(match.group(1))

            if dose>DOSE_RULES[name]:

                warnings.append(
                f"Dose may exceed safe limit for {name}"
                )

    return warnings


# ---------------------------
# Drug classification
# ---------------------------
def classify_drugs(drugs):

    classes={}

    for d in drugs:

        name=d.split()[0]

        drug_class=ATC_CLASSES.get(name,"Other")

        if drug_class not in classes:
            classes[drug_class]=0

        classes[drug_class]+=1

    return classes


# ---------------------------
# Safety score
# ---------------------------
def safety_score(drugs,interactions):

    score=100

    score-=len(drugs)*5

    for i in interactions:

        if i["severity"]=="moderate":
            score-=15

        if i["severity"]=="high":
            score-=30

    if score<0:
        score=0

    return score


# ---------------------------
# Clinical recommendations
# ---------------------------
def clinical_recommendations(risk,adr_level):

    rec=[]

    if risk=="high":
        rec.append("Avoid combination or consult clinical pharmacist")

    if adr_level=="high":
        rec.append("Monitor patient for adverse drug reactions")

    if len(rec)==0:
        rec.append("Prescription appears clinically safe")

    return rec


# ---------------------------
# RxNorm lookup
# ---------------------------
def rxnorm_lookup(drug):

    try:

        url=f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug}"

        r=requests.get(url)

        data=r.json()

        return data.get("idGroup",{}).get("rxnormId",[])

    except:

        return []


# ---------------------------
# Home
# ---------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------
# Analyze text prescription
# ---------------------------
@app.route("/analyze",methods=["POST"])
def analyze():

    data_req=request.get_json(silent=True) or {}

    text=data_req.get("text","")

    data=extract_info(text)

    interactions,interaction_risk=check_interactions(data["drugs"])

    poly_risk=polypharmacy_risk(data["drugs"])

    adr_level=adr_risk(data["age"],data["drugs"],interactions)

    edl_percent=edl_check(data["drugs"])

    who=who_indicators(data["drugs"])

    dose_warnings=dose_error(data["drugs"])

    classes=classify_drugs(data["drugs"])

    score=safety_score(data["drugs"],interactions)

    if "high" in [interaction_risk,poly_risk]:
        risk="high"
    elif "moderate" in [interaction_risk,poly_risk]:
        risk="moderate"
    else:
        risk="safe"

    recommendations=clinical_recommendations(risk,adr_level)

    return jsonify({
    "data":data,
    "interactions":interactions,
    "risk":risk,
    "adr_risk":adr_level,
    "polypharmacy":poly_risk,
    "safety_score":score,
    "drug_classes":classes,
    "edl_percent":edl_percent,
    "who_indicators":who,
    "dose_warnings":dose_warnings,
    "recommendations":recommendations
    })


# ---------------------------
# OCR prescription upload
# ---------------------------
@app.route("/upload",methods=["POST"])
def upload():

    file=request.files.get("file")

    if not file:
        return jsonify({"error":"No file uploaded"})

    image=Image.open(file)

    text=pytesseract.image_to_string(image)

    data=extract_info(text)

    interactions,interaction_risk=check_interactions(data["drugs"])

    score=safety_score(data["drugs"],interactions)

    return jsonify({
    "extracted_text":text,
    "interactions":interactions,
    "safety_score":score
    })


if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
