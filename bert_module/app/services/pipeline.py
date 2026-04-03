from app.utils.text_cleaner import clean_text
from app.utils.drug_matcher import find_drugs
from app.utils.biobert_ner import extract_medical_entities

def process_prescription(raw_text: str):
    
    # Step 1: Clean
    cleaned_text = clean_text(raw_text)
    
    # Step 2: Fuzzy
    fuzzy_drugs = find_drugs(cleaned_text)
    
    # Step 3: BioBERT
    bert_drugs = extract_medical_entities(raw_text)
    
    # Step 4: Combine
    final_drugs = list(set(fuzzy_drugs + bert_drugs))
    
    return {
        "cleaned_text": cleaned_text,
        "detected_drugs": final_drugs
    }
