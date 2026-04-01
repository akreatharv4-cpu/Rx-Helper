from bert_module.biobert import extract_medical_entities


def extract_drug_names(text):
    entities = extract_medical_entities(text)

    drugs = []
    current = ""

    for e in entities:
        word = e.get("word", "").strip()
        entity = str(e.get("entity", "")).upper()

        if not word:
            continue

        # Keep only likely medical/drug-like entities if model gives labels
        # If your BioBERT model does not return drug-specific labels, this still works
        # because we fall back to collecting cleaned tokens.
        if entity not in ["O"] and len(word) > 1:
            if word.startswith("##"):
                current += word[2:]
            else:
                if current:
                    drugs.append(current)
                current = word

    if current:
        drugs.append(current)

    # Clean duplicates and remove junk tokens
    cleaned = []
    seen = set()

    for d in drugs:
        d = d.strip()
        if len(d) < 3:
            continue
        if d not in seen:
            seen.add(d)
            cleaned.append(d)

    return cleaned


def extract_clean_drugs(text):
    raw_drugs = extract_drug_names(text)

    clean = []
    seen = set()

    for d in raw_drugs:
        d = d.strip()
        if len(d) < 3:
            continue
        if d.lower() not in seen:
            seen.add(d.lower())
            clean.append(d)

    return clean
