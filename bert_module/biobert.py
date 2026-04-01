from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# Load BioBERT model
MODEL_NAME = "dmis-lab/biobert-base-cased-v1.1"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

# Create NER pipeline
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer)


def extract_medical_entities(text):
    results = ner_pipeline(text)

    entities = []
    for r in results:
        entities.append({
            "word": r["word"],
            "entity": r["entity"],
            "score": float(r["score"])
        })

    return entities
