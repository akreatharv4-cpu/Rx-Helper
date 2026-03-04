from typing import List, Dict, Any

def compute_who(prescriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_prescriptions = len(prescriptions)
    total_drugs = 0

    generic_count = 0
    eml_count = 0

    abx_presc = 0
    inj_presc = 0

    for p in prescriptions:
        meds = p.get("extracted", {}).get("medications", [])
        total_drugs += len(meds)

        has_abx = any(m.get("is_antibiotic") for m in meds)
        has_inj = any(m.get("is_injection") for m in meds)
        if has_abx: abx_presc += 1
        if has_inj: inj_presc += 1

        generic_count += sum(1 for m in meds if m.get("is_generic_name"))
        eml_count += sum(1 for m in meds if m.get("is_eml"))

    avg_drugs = (total_drugs / total_prescriptions) if total_prescriptions else 0.0
    percent_generic = (generic_count / total_drugs * 100) if total_drugs else 0.0
    percent_eml = (eml_count / total_drugs * 100) if total_drugs else 0.0
    percent_abx = (abx_presc / total_prescriptions * 100) if total_prescriptions else 0.0
    percent_inj = (inj_presc / total_prescriptions * 100) if total_prescriptions else 0.0

    return {
        "total_prescriptions": total_prescriptions,
        "total_drugs": total_drugs,
        "avg_drugs_per_prescription": round(avg_drugs, 3),
        "percent_generic": round(percent_generic, 2),
        "percent_antibiotic_prescriptions": round(percent_abx, 2),
        "percent_injection_prescriptions": round(percent_inj, 2),
        "percent_eml": round(percent_eml, 2),
    }
