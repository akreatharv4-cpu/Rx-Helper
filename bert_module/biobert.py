from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

MODEL_NAME = "dmis-lab/biobert-base-cased-v1.1"


@lru_cache(maxsize=1)
def get_ner_pipeline():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    return pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple"
    )


def extract_medical_entities(text):
    ner_pipeline = get_ner_pipeline()
    return ner_pipeline(text)
