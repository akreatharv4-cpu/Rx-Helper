from transformers import pipeline

# Load model (runs first time slow)
ner = pipeline("ner", model="d4data/biomedical-ner-all")

def extract_medical_entities(text):
    results = ner(text)
    
    drugs = []
    
    for item in results:
        if item['entity'].lower() in ['drug', 'chemical']:
            drugs.append(item['word'])
    
    return drugs