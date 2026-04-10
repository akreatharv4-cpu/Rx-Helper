from bert_module.biobert import extract_medical_entities


ALLOWED_LABELS = {"chemical", "drug", "medication"}


def extract_clean_drugs(text):
    entities = extract_medical_entities(text)

    cleaned = []
    seen = set()

    for e in entities:
        label = str(e.get("entity_group", "")).lower().strip()
        if label not in ALLOWED_LABELS:
            continue

        word = str(e.get("word", "")).strip()
        if not word:
            continue

        word = word.replace("##", "")
        word = word.strip(" ,.;:()[]{}<>\"'")

        if len(word) < 3:
            continue

        key = word.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(word.upper())

    return cleaned