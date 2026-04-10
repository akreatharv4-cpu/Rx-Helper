from functools import lru_cache
from transformers import pipeline

MODEL_NAME = "d4data/biomedical-ner-all"


@lru_cache(maxsize=1)
def get_ner_pipeline():
    return pipeline(
        "ner",
        model=MODEL_NAME,
        aggregation_strategy="simple"
    )


def extract_medical_entities(text):
    if not text or not str(text).strip():
        return []

    try:
        ner_pipeline = get_ner_pipeline()
        return ner_pipeline(text)
    except Exception as e:
        print(f"BioBERT error: {e}")
        return []