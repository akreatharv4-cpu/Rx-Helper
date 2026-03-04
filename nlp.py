import re
from typing import Dict, Any, List, Optional

FREQ_PATTERNS = [
    r"\bOD\b", r"\bBD\b", r"\bTDS\b", r"\bQID\b",
    r"\bonce daily\b", r"\btwice daily\b", r"\bthrice daily\b",
    r"\bevery\s+\d+\s*(hours|hrs|h)\b",
]

ROUTE_HINTS = {
    "iv": "IV",
    "im": "IM",
    "po": "PO",
    "oral": "PO",
    "subcut": "SC",
    "sc": "SC",
    "topical": "TOP",
}

FORM_HINTS = ["tablet", "tab", "capsule", "cap", "syrup", "suspension", "inj", "injection", "cream", "ointment", "drops"]

def _clean_lines(text: str) -> List[str]:
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l and len(l) > 2]
    return lines

def _extract_patient_block(text: str) -> Dict[str, Optional[str]]:
    # Very lightweight heuristics
    name = None
    age = None
    sex = None
    weight = None
    date = None

    m = re.search(r"(?:name|patient)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if m:
        name = m.group(1).split("\n")[0].strip()

    m = re.search(r"\bage\s*[:\-]?\s*(\d{1,3})\b", text, re.IGNORECASE)
    if m:
        age = m.group(1)

    m = re.search(r"\b(sex|gender)\s*[:\-]?\s*(male|female|m|f)\b", text, re.IGNORECASE)
    if m:
        sex = m.group(2).upper()

    m = re.search(r"\bwt|weight\s*[:\-]?\s*(\d{2,3}(\.\d+)?)\s*(kg)?\b", text, re.IGNORECASE)
    if m:
        weight = m.group(1)

    m = re.search(r"\b(date)\s*[:\-]?\s*([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{2,4})\b", text, re.IGNORECASE)
    if m:
        date = m.group(2)

    return {"name": name, "age": age, "sex": sex, "weight_kg": weight, "date": date}

def _looks_like_med_line(line: str) -> bool:
    # contains dose units or form hints
    if re.search(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|units)\b", line, re.IGNORECASE):
        return True
    if any(h in line.lower() for h in FORM_HINTS):
        return True
    # Starts with Rx-like bullet/number
    if re.match(r"^(\d+[\).\s]|[-*]|rx\b)", line.lower()):
        return True
    return False

def _parse_med_line(line: str) -> Dict[str, Any]:
    original = line
    line = re.sub(r"^\s*(\d+[\).\s]+|[-*]\s+|rx[:\s]*)", "", line, flags=re.IGNORECASE).strip()

    strength = None
    m = re.search(r"(\d+(\.\d+)?)\s*(mg|mcg|g|ml|iu|units)\b", line, re.IGNORECASE)
    if m:
        strength = f"{m.group(1)} {m.group(3).lower()}"

    duration = None
    m = re.search(r"\bfor\s+(\d+)\s*(days|day|weeks|week|months|month)\b", line, re.IGNORECASE)
    if m:
        duration = f"{m.group(1)} {m.group(2).lower()}"

    freq = None
    for pat in FREQ_PATTERNS:
        m = re.search(pat, line, re.IGNORECASE)
        if m:
            freq = m.group(0)
            break

    route = None
    for k, v in ROUTE_HINTS.items():
        if re.search(rf"\b{k}\b", line, re.IGNORECASE):
            route = v
            break

    form = None
    for f in FORM_HINTS:
        if re.search(rf"\b{re.escape(f)}\b", line, re.IGNORECASE):
            form = f.lower()
            break

    # Drug name guess: take leading words until strength/form keyword
    stop_tokens = ["mg", "mcg", "g", "ml", "iu", "units"] + FORM_HINTS + ["po", "iv", "im", "sc", "od", "bd", "tds", "qid"]
    tokens = re.split(r"\s+", line)
    name_tokens = []
    for t in tokens:
        t_clean = re.sub(r"[^\w\-]", "", t).lower()
        if not t_clean:
            continue
        if t_clean in stop_tokens:
            break
        if re.match(r"^\d+(\.\d+)?$", t_clean):
            break
        name_tokens.append(t)
        if len(name_tokens) >= 5:
            break
    drug_name = " ".join(name_tokens).strip() or None

    return {
        "raw_line": original,
        "drug_name": drug_name,
        "strength": strength,
        "form": form,
        "route": route,
        "frequency": freq,
        "duration": duration,
    }

def extract_structured(text: str) -> Dict[str, Any]:
    patient = _extract_patient_block(text)
    lines = _clean_lines(text)

    meds = []
    for line in lines:
        if _looks_like_med_line(line):
            med = _parse_med_line(line)
            # avoid obvious non-meds
            if med["drug_name"] and len(med["drug_name"]) >= 2:
                meds.append(med)

    return {
        "patient": patient,
        "medications": meds,
        "meta": {
            "medication_count": len(meds),
        }
    }
