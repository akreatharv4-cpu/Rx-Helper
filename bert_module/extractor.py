from bert_module.biobert import extract_medical_entities


def extract_clean_drugs(text):
    entities = extract_medical_entities(text)

    words = []
    current = ""

    for e in entities:
        word = str(e.get("word", "")).strip()
        if not word:
            continue

        # Merge word pieces like "para" + "##cetamol"
        if word.startswith("##"):
            current += word[2:]
        else:
            if current:
                words.append(current)
            current = word

    if current:
        words.append(current)

    cleaned = []
    seen = set()

    for w in words:
        w = w.strip(" ,.;:()[]{}")
        if len(w) < 3:
            continue

        key = w.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(w)

    return cleaned
