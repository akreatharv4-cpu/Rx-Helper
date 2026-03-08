from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz


# ---------------- COMMON DRUG DATABASE ----------------

COMMON_ANTIBIOTICS = {
    "amoxicillin","azithromycin","ciprofloxacin","ceftriaxone",
    "doxycycline","metronidazole","cefixime","cephalexin"
}

INJECTION_HINT_FORMS = {"inj","injection"}

ESSENTIAL_MEDICINES = {
    "paracetamol","amoxicillin","metformin","oral rehydration salts",
    "ors","omeprazole","ceftriaxone","salbutamol"
}


# ---------------- DEMO DRUG INTERACTIONS ----------------

DDI_RULES = {
    tuple(sorted(("warfarin","metronidazole"))):(
        "major","Increased bleeding risk; monitor INR."
    ),

    tuple(sorted(("aceclofenac","warfarin"))):(
        "major","Bleeding risk increases with NSAIDs."
    ),

    tuple(sorted(("ibuprofen","warfarin"))):(
        "major","Bleeding risk increases with NSAIDs."
    ),
}


# ---------------- NORMALIZE DRUG NAME ----------------

def normalize_name(name: Optional[str]) -> Optional[str]:

    if not name:
        return None

    return " ".join(name.lower().split())


# ---------------- MEDICATION CLASSIFICATION ----------------

def classify_meds(extracted: Dict[str, Any]) -> Dict[str, Any]:

    meds = extracted.get("medications", [])

    for m in meds:

        name = normalize_name(m.get("drug_name"))

        m["normalized_name"] = name


        # antibiotic detection
        m["is_antibiotic"] = bool(
            name and any(
                fuzz.partial_ratio(name, ab) >= 90
                for ab in COMMON_ANTIBIOTICS
            )
        )


        # injection detection
        m["is_injection"] = bool(
            (m.get("route") in {"IV","IM","SC"})
            or (m.get("form") in INJECTION_HINT_FORMS)
            or ("inj" in (m.get("raw_line") or "").lower())
        )


        # generic name detection
        m["is_generic"] = bool(
            m.get("drug_name") and m["drug_name"].islower()
        )


        # essential medicines list detection
        m["is_eml"] = bool(
            name and any(
                fuzz.partial_ratio(name, eml) >= 90
                for eml in ESSENTIAL_MEDICINES
            )
        )

    return extracted


# ---------------- CLINICAL RULE FLAGS ----------------

def apply_flags(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:

    flags: List[Dict[str, Any]] = []

    meds = extracted.get("medications", [])
    patient = extracted.get("patient", {})


    # ---------- Missing fields ----------

    missing = []

    if not patient.get("name"):
        missing.append("patient.name")

    if not patient.get("age"):
        missing.append("patient.age")

    if len(meds) == 0:
        missing.append("medications")

    for i, m in enumerate(meds):

        if not m.get("drug_name"):
            missing.append(f"medications[{i}].drug_name")

        if not m.get("strength"):
            missing.append(f"medications[{i}].strength")

        if not m.get("frequency"):
            missing.append(f"medications[{i}].frequency")

        if not m.get("duration"):
            missing.append(f"medications[{i}].duration")


    if missing:

        flags.append({
            "type":"missing_fields",
            "severity":"moderate",
            "details":missing
        })


    # ---------- Polypharmacy ----------

    if len(meds) >= 5:

        flags.append({
            "type":"polypharmacy",
            "severity":"moderate",
            "details":{"medicine_count":len(meds)}
        })


    # ---------- Duplicate therapy ----------

    names = [
        m.get("normalized_name")
        for m in meds
        if m.get("normalized_name")
    ]

    duplicates = sorted({
        n for n in names if names.count(n) > 1
    })

    if duplicates:

        flags.append({
            "type":"duplicate_therapy",
            "severity":"moderate",
            "details":{"duplicates":duplicates}
        })


    # ---------- Drug interactions ----------

    ddis = []

    for i in range(len(names)):
        for j in range(i+1, len(names)):

            pair = tuple(sorted((names[i], names[j])))

            if pair in DDI_RULES:

                sev, msg = DDI_RULES[pair]

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
