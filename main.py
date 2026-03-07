from flask import Flask, request, jsonify, render_template
import re
import pandas as pd
import pytesseract
from PIL import Image
import requests
from ocr_medicine_detector import detect_medicines

app = Flask(**name**)

# Load interaction database

interactions_df = pd.read_csv("drug_interactions.csv")

# ---------------------------

# Essential Drug List

# ---------------------------

EDL = [
"paracetamol","amoxicillin","metformin","insulin",
"atorvastatin","aspirin","warfarin"
]

# ---------------------------

# ATC classification

# ---------------------------

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

# ---------------------
