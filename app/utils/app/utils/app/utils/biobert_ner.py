from transformers import pipeline

# Load ONCE (very important for FastAPI performance)
ner_pipeline = pipeline("ner", model="d4data/biomedical-ner-all")

def extract_medical_entities(text: str):
    results = ner_pipeline(text)
    
    drugs = []
    
    for item in results:
        label = item.get("entity", "").lower()
        
        if "drug" in label or "chemical" in label:
            drugs.append(item["word"])
    
    return drugs
