from transformers import pipeline
from utils.interaction_checker import check_interactions

# Load model (first run will download)
ner = pipeline("ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple")

def clean_entity(word):
    return word.replace("##", "").strip()

def extract_medical_entities(text):

    results = ner(text)

    drugs = []

    for item in results:
        if item["entity_group"].lower() in ["chemical", "drug"]:
            cleaned = clean_entity(item["word"])
            drugs.append(cleaned)

    # remove duplicates
    drugs = list(set(drugs))

    return drugs


# ---------------- MAIN EXECUTION ----------------

if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:])

    drugs = extract_medical_entities(text)

    interactions = check_interactions(drugs)

    print({
        "detected_drugs": [d.upper() for d in drugs],
        "interactions": interactions
    })