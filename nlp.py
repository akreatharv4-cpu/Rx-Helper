# medic_parser.py
import re
from typing import Dict, Any, List, Optional, Pattern

# ---------- Patterns / Hints ----------
FREQ_PATTERNS: List[Pattern] = [
    re.compile(r"\b(?:o\.?d\.?|once daily|once a day|daily)\b", re.IGNORECASE),
    re.compile(r"\b(?:b\.?d\.?|twice daily|twice a day|two times daily)\b", re.IGNORECASE),
    re.compile(r"\b(?:t\.?d\.?s?\.?|tds|thrice daily|three times daily)\b", re.IGNORECASE),
    re.compile(r"\b(?:q\.?id\.?|qid|four times daily)\b", re.IGNORECASE),
    re.compile(r"\b(?:at night|at bedtime)\b", re.IGNORECASE),
    re.compile(r"\bevery\s+(\d{1,2})\s*(?:hours|hrs|hr|h)\b", re.IGNORECASE),  # captures the number
    re.compile(r"\b(?:once|twice|thrice)\b\s*(?:daily|a day)?", re.IGNORECASE)
]

# route hints mapping (normalized value)
ROUTE_HINTS = {
    "iv": "IV",
    "i.v.": "IV",
    "im": "IM",
    "i.m.": "IM",
    "po": "PO",
    "p.o.": "PO",
    "oral": "PO",
    "subcut": "SC",
    "subcutaneous": "SC",
    "sc": "SC",
    "s.c.": "SC",
    "topical": "TOP",
    "pr": "PR",
    "sl": "SL",
}

FORM_HINTS = [
    "tablet", "tab", "tabs", "capsule", "cap", "caps", "syrup",
    "suspension", "susp", "inj", "injection", "cream", "ointment",
    "drops", "gel", "patch", "spray", "solution"
]

# unit normalization
UNIT_ALIASES = {
    "milligram": "mg", "milligrams": "mg", "mg": "mg",
    "microgram": "mcg", "mcg": "mcg", "μg": "mcg",
    "gram": "g", "g": "g",
    "ml": "ml", "mL": "ml",
    "iu": "IU", "units": "units"
}

# tokens that mark the end of the drug name
STOP_TOKENS = set(
    ["mg", "mcg", "g", "ml", "iu", "units"] +
    FORM_HINTS +
    list(ROUTE_HINTS.keys()) +
    ["od", "bd", "tds", "qid", "once", "twice", "daily", "hourly"]
)


# ---------- Helpers ----------
def _clean_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    # collapse multiple spaces and remove short junk lines
    lines = [re.sub(r"\s{2,}", " ", l) for l in lines]
    lines = [l for l in lines if l and len(l) > 2]
    return lines


def _normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    u = unit.lower().strip().replace(".", "")
    return UNIT_ALIASES.get(u, u)


def _normalize_strength(amount: str, unit: Optional[str]) -> Optional[str]:
    if not amount:
        return None
    unit_norm = _normalize_unit(unit) or ""
    return f"{amount} {unit_norm}".strip()


# ---------- Patient block extraction ----------
def _extract_patient_block(text: str) -> Dict[str, Optional[str]]:
    """
    Lightweight extraction for common patient fields.
    Returns keys: name, age, sex, weight_kg, date
    """
    name = None
    age = None
    sex = None
    weight = None
    date = None

    # Name: "Name: John Doe" or "Patient: John Doe"
    m = re.search(r"^(?:name|patient)\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        name = m.group(1).strip()

    # Age: "Age: 45" or "Age-45yrs"
    m = re.search(r"\bage\s*[:\-]?\s*(\d{1,3})\b", text, flags=re.IGNORECASE)
    if m:
        age = m.group(1)

    # Sex/Gender
    m = re.search(r"\b(?:sex|gender)\s*[:\-]?\s*(male|female|m|f)\b", text, flags=re.IGNORECASE)
    if m:
        sex_token = m.group(1).lower()
        sex = "M" if sex_token.startswith("m") else "F"

    # Weight: "Wt: 70 kg" or "weight: 70kg"
    m = re.search(r"\b(?:wt|weight)\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s*(kg|kgs)?\b", text, flags=re.IGNORECASE)
    if m:
        weight = m.group(1)

    # Date: allow common separators DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.search(r"\b(?:date)\s*[:\-]?\s*([0-3]?\d[\/\-\.\s][01]?\d[\/\-\.\s]\d{2,4})\b", text, flags=re.IGNORECASE)
    if m:
        date = m.group(1).strip()

    return {"name": name, "age": age, "sex": sex, "weight_kg": weight, "date": date}


# ---------- Med line detection ----------
def _looks_like_med_line(line: str) -> bool:
    # contains dose units or form hints
    if re.search(r"\b\d+(\.\d+)?\s*(?:mg|mcg|g|ml|iu|units)\b", line, re.IGNORECASE):
        return True
    if any(re.search(rf"\b{re.escape(h)}\b", line, flags=re.IGNORECASE) for h in FORM_HINTS):
        return True
    # starts with numbering or bullet or Rx:
    if re.match(r"^\s*(?:\d+[\).\s]+|[-*\u2022]\s+|rx[:\s])", line, flags=re.IGNORECASE):
        return True
    # short lines with drug-like tokens
    if 3 <= len(line) <= 60 and re.search(r"[A-Za-z]{3,}", line):
        # heuristics only; keep conservative
        return bool(re.search(r"[A-Za-z]+\s+\d", line))
    return False


# ---------- Parse a single medicine line ----------
def _parse_med_line(line: str) -> Dict[str, Any]:
    """
    Extract: drug_name, strength, form, route, frequency, duration, raw_line
    """
    original = line
    # remove leading bullets / numbers / rx:
    line = re.sub(r"^\s*(?:\d+[\).\s]+|[-*\u2022]\s+|rx[:\s]*)", "", line, flags=re.IGNORECASE).strip()

    # find strength: amount + unit
    strength_amount = None
    strength_unit = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|mcg|μg|g|ml|iu|units)\b", line, flags=re.IGNORECASE)
    if m:
        strength_amount = m.group(1)
        strength_unit = _normalize_unit(m.group(2))

    strength = _normalize_strength(strength_amount or "", strength_unit)

    # duration: "for 5 days", "5 days", "x 5 days", "5d", "for 2 wks"
    duration = None
    m = re.search(r"\b(?:for\s+)?(\d{1,3})\s*(?:days?|d\b|weeks?|wks?|months?)\b", line, flags=re.IGNORECASE)
    if m:
        qty = m.group(1)
        unit = re.search(r"(days?|d\b|weeks?|wks?|months?)", line, flags=re.IGNORECASE)
        unit_text = unit.group(0) if unit else "days"
        duration = f"{qty} {unit_text.lower()}"

    # frequency detection & normalization
    frequency_raw = None
    frequency_norm = None
    for pat in FREQ_PATTERNS:
        m = pat.search(line)
        if m:
            frequency_raw = m.group(0)
            # normalize special case for "every N hours"
            every_match = re.match(r"every\s+(\d{1,2})", m.group(0), flags=re.IGNORECASE)
            if every_match:
                frequency_norm = f"every {every_match.group(1)} hours"
            else:
                frequency_norm = m.group(0).lower()
            break

    # route
    route = None
    for token, norm in ROUTE_HINTS.items():
        if re.search(rf"\b{re.escape(token)}\b", line, flags=re.IGNORECASE):
            route = norm
            break

    # form
    form = None
    for f in FORM_HINTS:
        if re.search(rf"\b{re.escape(f)}\b", line, flags=re.IGNORECASE):
            form = f.lower()
            break

    # drug name guess: tokens until a stop token (strength/unit/form/route/frequency)
    tokens = re.split(r"\s+", line)
    name_tokens: List[str] = []
    for t in tokens:
        t_clean = re.sub(r"[^\w\-]", "", t).lower()
        if not t_clean:
            continue
        if t_clean in STOP_TOKENS:
            break
        # numeric tokens likely not part of the drug name
        if re.match(r"^\d+(\.\d+)?$", t_clean):
            break
        name_tokens.append(t)
        if len(name_tokens) >= 6:
            break
    drug_name = " ".join(name_tokens).strip() or None
    # tidy drug name (remove trailing punctuation)
    if drug_name:
        drug_name = re.sub(r"[^\w\s\-]", "", drug_name).strip()

    # Build record
    record = {
        "raw_line": original,
        "drug_name": drug_name,
        "strength": strength,
        "form": form,
        "route": route,
        "frequency_raw": frequency_raw,
        "frequency": frequency_norm,
        "duration": duration,
        "confidence": 1.0,  # placeholder — you can fill with OCR / model confidence later
    }
    return record


# ---------- Top-level extractor ----------
def extract_structured(text: str) -> Dict[str, Any]:
    """
    Extract patient block and medication lines from raw OCR text.
    Returns:
    {
      "patient": {name, age, sex, weight_kg, date},
      "medications": [ {drug_name, strength, form, route, frequency, duration, raw_line}, ... ],
      "meta": { medication_count: int }
    }
    """
    patient = _extract_patient_block(text)
    lines = _clean_lines(text)

    meds: List[Dict[str, Any]] = []
    for line in lines:
        try:
            if _looks_like_med_line(line):
                parsed = _parse_med_line(line)
                # simple guard: drug_name must be present and at least 2 chars
                if parsed.get("drug_name") and len(parsed["drug_name"]) >= 2:
                    meds.append(parsed)
        except Exception:
            # preserve robustness: skip lines that throw parsing errors
            continue

    return {
        "patient": patient,
        "medications": meds,
        "meta": {
            "medication_count": len(meds)
        }
    }


# ---------- Quick local test ----------
if __name__ == "__main__":
    sample = """
    Patient: John Doe
    Age: 45
    Sex: M
    Date: 12/03/2026

    1. Amoxicillin 500 mg BD for 5 days
    2. Paracetamol 650 mg TDS as needed
    Salbutamol inhaler 2 puffs PRN
    Inj. Diclofenac 75 mg IM stat
    """
    out = extract_structured(sample)
    import json
    print(json.dumps(out, indent=2))
    
