from typing import List, Dict

# ✅ WHO INDICATORS (added safely)
WHO_INDICATORS = [
    {
        "id": "avg_drugs",
        "indicator": "Average number of drugs per encounter",
        "target": "1.6-1.8",
        "formula": "Total drugs / Total encounters",
        "unit": "count"
    },
    {
        "id": "pct_generic",
        "indicator": "Percentage of drugs prescribed by generic name",
        "target": "100%",
        "formula": "(Generic drugs / Total drugs) * 100",
        "unit": "%"
    },
    {
        "id": "pct_antibiotic",
        "indicator": "Encounters with antibiotic prescribed",
        "target": "20.0-26.8%",
        "formula": "(Encounters with at least 1 antibiotic / Total encounters) * 100",
        "unit": "%"
    },
    {
        "id": "pct_injection",
        "indicator": "Encounters with injection prescribed",
        "target": "13.4-24.1%",
        "formula": "(Encounters with at least 1 injection / Total encounters) * 100",
        "unit": "%"
    },
    {
        "id": "pct_eml",
        "indicator": "Percentage of drugs from Essential Drug List",
        "target": "100%",
        "formula": "(Drugs from EDL / Total drugs) * 100",
        "unit": "%"
    }
]


class ClinicalAuditor:
    def __init__(self, db_session):
        self.db = db_session

    def generate_prescribing_indicators(self, encounter_data):
        """4. Clinical Auditing: WHO Rational Use Metrics"""

        total_encounters = len(encounter_data)
        total_drugs = sum(len(e.prescriptions) for e in encounter_data)

        # ✅ Safe calculations (avoid division by zero)
        if total_encounters == 0 or total_drugs == 0:
            return {
                "average_drugs_per_encounter": 0,
                "percentage_antibiotic_encounters": 0,
                "percentage_injection_encounters": 0,
                "percentage_essential_medicines": 0,
                "percentage_generic_prescribing": 0,
                "who_targets": WHO_INDICATORS  # attach reference
            }

        antibiotic_encounters = sum(
            1 for e in encounter_data
            if any(getattr(rx, "is_antibiotic", False) for rx in e.prescriptions)
        )

        injection_encounters = sum(
            1 for e in encounter_data
            if any(getattr(rx, "route", "") in ["IM", "IV", "IM/IV"] for rx in e.prescriptions)
        )

        eml_drugs = sum(
            1 for e in encounter_data
            for rx in e.prescriptions
            if getattr(rx, "is_essential", False)
        )

        generic_drugs = sum(
            1 for e in encounter_data
            for rx in e.prescriptions
            if getattr(rx, "prescribed_as_generic", False)
        )

        results = {
            "average_drugs_per_encounter": round(total_drugs / total_encounters, 2),
            "percentage_antibiotic_encounters": round((antibiotic_encounters / total_encounters) * 100, 2),
            "percentage_injection_encounters": round((injection_encounters / total_encounters) * 100, 2),
            "percentage_essential_medicines": round((eml_drugs / total_drugs) * 100, 2),
            "percentage_generic_prescribing": round((generic_drugs / total_drugs) * 100, 2),
        }

        # ✅ Attach WHO benchmarks
        return {
            "results": results,
            "who_targets": WHO_INDICATORS
        }

    def run_deep_audit_checks(self, prescription):
        """4. Deep Audit Checks: Unnecessary polypharmacy, missed prophylaxis"""

        flags = []

        # ✅ Safe attribute access
        if getattr(prescription, "indication", None) not in getattr(prescription, "approved_indications", []):
            flags.append(f"Off-label or unverified indication for {getattr(prescription, 'generic_name', 'unknown drug')}.")

        if len(getattr(prescription, "current_medications", [])) > 5:
            flags.append("Polypharmacy Alert: Patient on >5 concurrent medications. Review required.")

        return flags