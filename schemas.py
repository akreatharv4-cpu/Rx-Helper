from pydantic import BaseModel, Field, validator
from typing import Any, Optional, List, Dict, Union
from datetime import datetime
from enum import Enum

# --- 1. CLINICAL ENUMS ---
# Using Enums ensures the database and frontend always use the same terms.

class AlertSeverity(str, Enum):
    INFO = "info"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"

class AlertType(str, Enum):
    INTERACTION = "drug_drug_interaction"
    OVERDOSE = "dosage_safety"
    CONTRAINDICATION = "contraindication"
    DUPLICATION = "therapeutic_duplication"

# --- 2. SUB-MODELS (The Building Blocks) ---

class PatientContext(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    weight_kg: Optional[float] = None
    crcl_ml_min: Optional[float] = Field(None, description="Creatinine Clearance")
    is_pregnant: bool = False
    is_lactating: bool = False

class ExtractedDrug(BaseModel):
    name: str
    strength: Optional[str] = None  # e.g., "500mg"
    frequency: Optional[str] = None # e.g., "TID"
    route: str = "Oral"             # Default to Oral
    duration_days: Optional[int] = None
    is_generic: bool = False
    is_antibiotic: bool = False
    is_injection: bool = False
    is_essential: bool = False      # Matches EDL/EML status

class ClinicalFlag(BaseModel):
    type: AlertType
    severity: AlertSeverity
    drug_involved: List[str]
    message: str
    clinical_reference: Optional[str] = "WHO/BNF Guidelines"

# --- 3. UPGRADED REQUEST MODEL ---

class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=10)
    filename: Optional[str] = "manual_entry.txt"
    patient_info: PatientContext = Field(default_factory=PatientContext)
    clinic_id: Optional[str] = "AMR-GCP-01" # Audit tracking for your college

# --- 4. UPGRADED PRESCRIPTION OUTPUT ---

class PrescriptionOut(BaseModel):
    id: str  # UUID or tracking number
    timestamp: datetime = Field(default_factory=datetime.now)
    source_filename: Optional[str] = None
    raw_text_preview: str
    
    # Strictly typed objects instead of Dict[str, Any]
    detected_drugs: List[ExtractedDrug]
    safety_alerts: List[ClinicalFlag]
    
    # Summary of indicators for this specific encounter
    encounter_indicators: Dict[str, Union[int, float, bool]]

# --- 5. ADVANCED WHO METRICS (Population Level) ---

class WhoMetricsOut(BaseModel):
    report_period_start: datetime
    report_period_end: datetime
    
    # Core WHO Indicators
    total_encounters_audited: int
    avg_drugs_per_encounter: float = Field(..., description="WHO Norm: 1.6-1.8")
    
    # Percentages
    pc_generic_prescribed: float    # WHO Norm: 100%
    pc_antibiotic_encounters: float # WHO Norm: < 30%
    pc_injection_encounters: float  # WHO Norm: < 20%
    pc_edl_compliance: float        # WHO Norm: 100%
    
    # Facility Indicators
    is_edl_available: bool = True
    total_cost_per_encounter: Optional[float] = None