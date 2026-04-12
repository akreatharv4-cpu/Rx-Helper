import pandas as pd
from typing import List, Dict, Any

class AdvancedSafetyEngine:
    def __init__(self, interactions_df: pd.DataFrame, medicines_df: pd.DataFrame):
        """
        Initializes the Safety Engine using Pandas DataFrames instead of an SQL DB.
        Pass your loaded drug_interactions.csv and medicines_master.csv here.
        """
        self.interactions_df = interactions_df
        self.medicines_df = medicines_df

    def _get_generic_name(self, rx: Any) -> str:
        """Helper to safely get the generic name whether rx is an object or dictionary."""
        if isinstance(rx, dict):
            return str(rx.get('generic_name', rx.get('name', ''))).strip().lower()
        return str(getattr(rx, 'generic_name', getattr(rx, 'name', ''))).strip().lower()

    def _get_drug_class(self, rx: Any) -> str:
        """Helper to safely get the drug class."""
        if isinstance(rx, dict):
            return str(rx.get('drug_class', rx.get('class', ''))).strip()
        return str(getattr(rx, 'drug_class', getattr(rx, 'class', ''))).strip()

    def run_comprehensive_check(self, prescription: List[Any], patient_profile: Dict[str, Any], patient_labs: Dict[str, Any]) -> Dict[str, List[str]]:
        """5. Advanced Safety Engine Core Function"""
        alerts = {
            "critical_flags": [],
            "warnings": [],
            "info": []
        }
        
        if not prescription:
            return alerts

        # Fetch the specific alerts
        drug_alerts = self._check_drug_interactions(prescription)
        lab_alerts = self._check_lab_aware_safety(prescription, patient_labs)
        pop_alerts = self._check_special_populations(prescription, patient_profile)
        
        # Safely merge lists together so we don't overwrite/delete alerts
        for key in alerts.keys():
            alerts[key].extend(drug_alerts.get(key, []))
            alerts[key].extend(lab_alerts.get(key, []))
            alerts[key].extend(pop_alerts.get(key, []))
        
        return alerts

    def _check_drug_interactions(self, prescription: List[Any]) -> Dict[str, List[str]]:
        """5A. Drug Safety Checks using Pandas DataFrame (CSV data)"""
        alerts = {"critical_flags": [], "warnings": [], "info": []}
        
        prescribed_generics = [self._get_generic_name(rx) for rx in prescription if rx]
        prescribed_generics = [g for g in prescribed_generics if g] # Filter empties
        
        # Check Therapeutic Duplication
        classes = [self._get_drug_class(rx) for rx in prescription if rx]
        classes = [c for c in classes if c] # Filter empties
        if len(classes) != len(set(classes)) and len(classes) > 0:
            alerts["warnings"].append("Therapeutic Duplication detected: Multiple drugs from the same class.")

        # Check Drug-Drug Interactions from Pandas DataFrame
        if not self.interactions_df.empty and len(prescribed_generics) > 1:
            # Check every pair of prescribed drugs
            for i in range(len(prescribed_generics)):
                for j in range(i + 1, len(prescribed_generics)):
                    drug1 = prescribed_generics[i]
                    drug2 = prescribed_generics[j]
                    
                    # Search DataFrame for this specific pair
                    match = self.interactions_df[
                        ((self.interactions_df['drug1'] == drug1) & (self.interactions_df['drug2'] == drug2)) |
                        ((self.interactions_df['drug1'] == drug2) & (self.interactions_df['drug2'] == drug1))
                    ]
                    
                    if not match.empty:
                        for _, row in match.iterrows():
                            severity = str(row.get('severity', 'MODERATE')).upper()
                            message = str(row.get('message', 'Potential interaction.'))
                            
                            alert_msg = f"Interaction: {drug1.title()} + {drug2.title()}. {message}"
                            
                            if severity in ["HIGH", "SEVERE", "CONTRAINDICATED"]:
                                alerts["critical_flags"].append(f"[SEVERE] {alert_msg}")
                            else:
                                alerts["warnings"].append(f"[{severity}] {alert_msg}")

        return alerts

    def _check_lab_aware_safety(self, prescription: List[Any], patient_labs: Dict[str, Any]) -> Dict[str, List[str]]:
        """5C. Expanded Lab-Aware Safety: eGFR, LFTs, INR, K+"""
        alerts = {"critical_flags": [], "warnings": [], "info": []}
        
        if not patient_labs:
            return alerts
            
        for rx in prescription:
            generic_name = self._get_generic_name(rx)
            drug_class = self._get_drug_class(rx).lower()

            # 1. Renal Impairment (eGFR)
            if patient_labs.get('eGFR', 100) < 30:
                if generic_name in ['metformin', 'gabapentin', 'pregabalin', 'rivaroxaban']:
                    alerts["critical_flags"].append(
                        f"Contraindication/Dose Adjust: {generic_name.title()} requires review for eGFR < 30. Current eGFR: {patient_labs['eGFR']}"
                    )
                    
            # 2. Hyperkalemia Risk
            if "potassium-sparing" in drug_class or "arb" in drug_class or "ace inhibitor" in drug_class:
                if patient_labs.get('Potassium', 4.0) > 5.0:
                     alerts["critical_flags"].append(
                        f"Risk of Hyperkalemia: {generic_name.title()} prescribed with elevated serum K+ ({patient_labs['Potassium']})."
                    )

            # 3. Hepatic Impairment (Liver Function Tests)
            if patient_labs.get('ALT', 40) > 150 or patient_labs.get('AST', 40) > 150:
                if "statin" in drug_class or generic_name == "paracetamol" or generic_name == "amoxicillin_clavulanate":
                    alerts["warnings"].append(
                        f"Hepatotoxicity Risk: Elevated LFTs detected while prescribing {generic_name.title()}."
                    )

            # 4. Coagulation (INR) for Warfarin
            if generic_name == "warfarin" and patient_labs.get('INR', 1.0) > 3.5:
                alerts["critical_flags"].append(
                    f"Bleeding Risk: Warfarin prescribed with supratherapeutic INR ({patient_labs['INR']})."
                )

        return alerts
        
    def _check_special_populations(self, prescription: List[Any], patient_profile: Dict[str, Any]) -> Dict[str, List[str]]:
        """5B. Expanded Special Population Checks (Pediatrics, Geriatrics, Pregnancy, Lactation)"""
        alerts = {"critical_flags": [], "warnings": [], "info": []}
        
        if not patient_profile:
            return alerts
            
        age = patient_profile.get('age', 30)
        is_pregnant = patient_profile.get('is_pregnant', False)
        is_lactating = patient_profile.get('is_lactating', False)
        
        for rx in prescription:
            generic_name = self._get_generic_name(rx)
            drug_class = self._get_drug_class(rx).lower()

            # 1. Pregnancy Contraindications (Teratogens)
            if is_pregnant:
                teratogens = [
                    "warfarin", "methotrexate", "isotretinoin", "valproate", 
                    "lisinopril", "losartan", "enalapril", "valsartan", 
                    "atorvastatin", "rosuvastatin", "simvastatin", 
                    "carbamazepine", "lithium", "thalidomide", "misoprostol"
                ]
                if generic_name in teratogens or "statin" in drug_class or "ace inhibitor" in drug_class or "arb" in drug_class:
                    alerts["critical_flags"].append(f"PREGNANCY CONTRAINDICATION: {generic_name.title()} is strongly contraindicated during pregnancy.")

            # 2. Lactation / Breastfeeding Warnings
            if is_lactating:
                lactation_risks = ["amiodarone", "lithium", "methotrexate", "codeine", "tramadol"]
                if generic_name in lactation_risks:
                    alerts["critical_flags"].append(f"LACTATION WARNING: {generic_name.title()} poses a high risk to the infant during breastfeeding.")

            # 3. Pediatric Warnings
            if age < 18:
                if generic_name == "aspirin" and age < 16:
                    alerts["critical_flags"].append(f"Pediatric Contraindication: Aspirin in patients < 16 carries risk of Reye's Syndrome.")
                if generic_name in ["codeine", "tramadol"] and age < 12:
                    alerts["critical_flags"].append(f"Pediatric Contraindication: {generic_name.title()} is contraindicated in children < 12 due to respiratory depression risk.")
            
            if age < 12:
                if "fluoroquinolone" in drug_class or generic_name in ["ciprofloxacin", "levofloxacin"]:
                    alerts["warnings"].append(f"Pediatric Warning: {generic_name.title()} may cause cartilage damage in patients under 12.")
                if generic_name in ["doxycycline", "tetracycline"] and age < 8:
                    alerts["critical_flags"].append(f"Pediatric Contraindication: {generic_name.title()} can cause permanent tooth discoloration in patients under 8.")
                    
            # 4. Geriatric Warnings (Beers Criteria - Over 65 years old)
            if age >= 65:
                # Anticholinergics
                if "antihistamine" in drug_class and generic_name in ["diphenhydramine", "promethazine", "chlorpheniramine"]:
                    alerts["warnings"].append(f"Geriatric Warning (Beers Criteria): {generic_name.title()} carries high anticholinergic risk in patients >= 65.")
                
                # CNS Depressants (Falls/Cognition)
                if generic_name in ["zolpidem", "clonazepam", "diazepam", "lorazepam", "alprazolam"]:
                    alerts["warnings"].append(f"Geriatric Warning (Beers Criteria): {generic_name.title()} increases risk of falls, delirium, and cognitive impairment.")
                
                # NSAIDs (GI Bleeding/Renal)
                if generic_name in ["ibuprofen", "diclofenac", "naproxen", "meloxicam", "indomethacin"]:
                    alerts["warnings"].append(f"Geriatric Warning: Chronic use of {generic_name.title()} in older adults increases risk of GI bleeding and renal injury.")
                
                # Sulfonylureas (Hypoglycemia)
                if generic_name in ["glimepiride", "glipizide", "glyburide", "gliclazide"]:
                    alerts["warnings"].append(f"Geriatric Warning: {generic_name.title()} has a high risk of prolonged hypoglycemia in older adults.")

        return alerts