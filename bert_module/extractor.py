from bert_module.biobert import extract_medical_entities


def extract_drug_names(text):
    entities = extract_medical_entities(text)

    drugs = []

    for e in entities:
        word = e["word"]

        # Basic cleaning (remove ## from tokens)
        if word.startswith("##"):
            if drugs:
                drugs[-1] += word[2:]
        else:
            drugs.append(word)

    return drugs


def extract_clean_drugs(text):
    raw_drugs = extract_drug_names(text)

    # Remove duplicates and clean
    clean = list(set([d.strip() for d in raw_drugs if len(d) > 2]))

    return clean
