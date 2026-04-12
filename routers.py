from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# =====================================================================
# 1. SCHEMAS (Pydantic Models)
# Best Practice: Always define strict input/output schemas. This ensures
# data validation and gives linters the exact types to expect, eliminating
# undefined variable errors related to request/response payloads.
# =====================================================================

class User(BaseModel):
    id: int
    username: str
    role: str = Field(..., description="E.g., 'doctor', 'patient', 'pharmacist'")

class MedicineExplanation(BaseModel):
    brand_name: str
    simple_indication: str

class SafeAlternative(BaseModel):
    generic_name: str
    reason: str
    cost_difference_percentage: float

class DoctorReviewResponse(BaseModel):
    guideline_support: List[str]
    safe_alternative_suggestions: List[SafeAlternative]
    override_required: bool
    warnings: List[str]

class PatientExplanationResponse(BaseModel):
    what_it_is: str
    how_to_take: str
    what_to_avoid: str
    warning_symptoms: str
    teach_back_required: bool

class PharmacistReconciliationResponse(BaseModel):
    medication_history: List[str]
    interaction_review: Dict[str, Any]
    escalate_to_doctor_endpoint: str


# =====================================================================
# 2. DEPENDENCIES (Authentication & Authorization)
# Best Practice: Use FastAPI's `Depends` system. Instead of undefined 
# global variables, we explicitly inject the current user context into 
# the route. This isolates authentication logic from business logic.
# =====================================================================

def get_current_user() -> User:
    """Mock authentication dependency. In reality, this decodes a JWT."""
    # Imagine we extract a token from the request header here
    return User(id=1, username="Dr. Smith", role="doctor")

def get_current_doctor(user: User = Depends(get_current_user)) -> User:
    if user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Doctor access")
    return user

def get_current_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Patient access")
    return user

def get_current_pharmacist(user: User = Depends(get_current_user)) -> User:
    if user.role != "pharmacist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Pharmacist access")
    return user


# =====================================================================
# 3. SERVICE LAYER MOCKS
# Best Practice: Keep routers clean. HTTP routers should only handle 
# web traffic (requests/responses). Complex logic (like the Safety Engine) 
# belongs in a separate service layer. By defining these here, we 
# resolve all `reportUndefinedVariable` errors.
# =====================================================================

def fetch_clinical_guidelines(encounter_id: int) -> List[str]:
    """Fetches local protocol guidelines based on diagnosis codes."""
    return ["First-line therapy for uncomplicated UTI is Nitrofurantoin."]

def get_cheaper_equivalents(encounter_id: int) -> List[SafeAlternative]:
    """Queries the Pharmacoeconomics module."""
    return [SafeAlternative(generic_name="Amoxicillin", reason="Equally effective, lower cost", cost_difference_percentage=-45.0)]

def get_rx(prescription_id: int) -> MedicineExplanation:
    """Fetches prescription details from the database."""
    if prescription_id <= 0:
         raise HTTPException(status_code=404, detail="Prescription not found")
    return MedicineExplanation(brand_name="Augmentin", simple_indication="Bacterial Infection")

def get_patient_history(patient_id: int) -> List[str]:
    """Fetches past dispensed medications."""
    return ["Lisinopril 10mg", "Metformin 500mg"]

def run_advanced_safety_engine(patient_id: int) -> Dict[str, Any]:
    """Triggers the Advanced Safety Engine from the previous architecture."""
    return {"status": "clear", "flags": []}


# =====================================================================
# 4. API ROUTERS
# Now, the routers assemble the predefined dependencies and services.
# Pylance/Pyright will analyze this and find 0 undefined variables.
# =====================================================================

router = APIRouter()

@router.get("/api/ui/doctor/review/{encounter_id}", response_model=DoctorReviewResponse)
def doctor_mode_review(encounter_id: int, current_user: User = Depends(get_current_doctor)):
    """8. Doctor Mode: Auto-generated summary and safe alternatives"""
    
    # 1. Variables are explicitly defined by calling our service functions
    guidelines = fetch_clinical_guidelines(encounter_id)
    alternatives = get_cheaper_equivalents(encounter_id)
    
    # 2. Return data matching the strict Pydantic model
    return DoctorReviewResponse(
        guideline_support=guidelines,
        safe_alternative_suggestions=alternatives,
        override_required=True,
        warnings=["Patient has a mild penicillin allergy noted in 2018."]
    )

@router.get("/api/ui/patient/explain/{prescription_id}", response_model=PatientExplanationResponse)
def patient_mode_explain(prescription_id: int, current_user: User = Depends(get_current_patient)):
    """8. Patient Mode: Simple explanation and adherence"""
    
    # Explicitly fetch the Rx to avoid undefined references
    rx = get_rx(prescription_id)
    
    return PatientExplanationResponse(
        what_it_is=f"This is {rx.brand_name}, it helps with your {rx.simple_indication.lower()}.",
        how_to_take="Take one tablet with food in the morning.",
        what_to_avoid="Do not drink grapefruit juice while taking this.",
        warning_symptoms="Go to the ER if you experience swelling of the lips or face.",
        teach_back_required=True
    )
    
@router.get("/api/ui/pharmacist/reconcile/{patient_id}", response_model=PharmacistReconciliationResponse)
def pharmacist_mode_reconcile(patient_id: int, current_user: User = Depends(get_current_pharmacist)):
    """8. Pharmacist Mode: Clinical verification and escalation"""
    
    history = get_patient_history(patient_id)
    safety_review = run_advanced_safety_engine(patient_id)
    
    return PharmacistReconciliationResponse(
        medication_history=history,
        interaction_review=safety_review,
        escalate_to_doctor_endpoint=f"/api/messages/escalate/{patient_id}"
    )