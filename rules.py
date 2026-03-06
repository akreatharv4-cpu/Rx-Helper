from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz

COMMON_ANTIBIOTICS = {
    "amoxicillin","azithromycin","ciprofloxacin","ceftriaxone",
    "doxycycline","metronidazole","cefixime","cephalexin"
}

INJECTION_HINT_FORMS = {"inj","injection"}

ESSENTIAL_MEDICINES_DEMO = {
    "paracetamol","amoxicillin","metformin","oral rehydration salts",
    "ors","omeprazole","ceftriaxone","salbutamol"
}

DDI_DEMO = {
    tuple(sorted(("warfarin","metronidazole"))):(
        "major","Increased bleeding risk; monitor INR/avoid."
    ),
    tuple(sorted(("aceclofenac","warfarin"))):(
        "major","Bleeding risk increases with NSAIDs."
    ),
    tuple(sorted(("ibuprofen","warfarin"))):(
        "major","Bleeding risk increases with NSAIDs."
    ),
}

def _norm_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return " ".join(name.lower().split())


def classify_meds(extracted: Dict[str, Any]) -> Dict[str, Any]:

    meds = extracted.get("medications", [])

    for m in meds:

        n = _norm_name(m.get("drug_name"))
        m["normalized_name"] = n

        m["is_antibiotic"] = bool(
            n and any(fuzz.partial_ratio(n, ab) >= 90 for ab in COMMON_ANTIBIOTICS)
        )

        m["is_injection"] = bool(
            (m.get("route") in {"IV","IM","SC"})
            or (m.get("form") in INJECTION_HINT_FORMS)
            or ("inj" in (m.get("raw_line") or "").lower())
        )

        m["is_generic_name"] = bool(
            m.get("drug_name") and m["drug_name"].islower()
        )

        m["is_eml"] = bool(
            n and any(fuzz.partial_ratio(n, eml) >= 90 for eml in ESSENTIAL_MEDICINES_DEMO)
        )

    return extracted


def apply_flags(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:

    flags: List[Dict[str, Any]] = []
    meds = extracted.get("medications", [])
    patient = extracted.get("patient", {})

    missing = []

    if not patient.get("name"):
        missing.append("patient.name")

    if not patient.get("age"):
        missing.append("patient.age")

    if len(meds) == 0:
        missing.append("medications")

    for idx, m in enumerate(meds):

        if not m.get("drug_name"):
            missing.append(f"medications[{idx}].drug_name")

        if not m.get("strength"):
            missing.append(f"medications[{idx}].strength")

        if not m.get("frequency"):
            missing.append(f"medications[{idx}].frequency")

        if not m.get("duration"):
            missing.append(f"medications[{idx}].duration")

    if missing:
        flags.append({
            "type":"missing_fields",
            "severity":"moderate",
            "details":missing
        })

    if len(meds) >= 5:
        flags.append({
            "type":"polypharmacy",
            "severity":"moderate",
            "details":{"med_count":len(meds)}
        })

    names = [m.get("normalized_name") for m in meds if m.get("normalized_name")]

    dupes = sorted({n for n in names if names.count(n) > 1})

    if dupes:
        flags.append({
            "type":"duplicate_therapy",
            "severity":"moderate",
            "details":{"duplicates":dupes}
        })

    normalized = [n for n in names if n]

    ddis = []

    for i in range(len(normalized)):
        for j in range(i+1,len(normalized)):

            pair = tuple(sorted((normalized[i],normalized[j])))

            if pair in DDI_DEMO:

                sev,msg = DDI_DEMO[pair]

                ddis.append({
                    "pair":list(pair),
                    "severity":sev,
                    "message":msg
                })

    if ddis:
        flags.append({
            "type":"drug_drug_interactions",
            "severity":"major",
            "details":ddis
        })

    return flags
