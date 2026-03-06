from pydantic import BaseModel
from typing import Any, Optional, List, Dict
from datetime import datetime


class AnalyzeTextRequest(BaseModel):
    text: str
    filename: Optional[str] = None


class PrescriptionOut(BaseModel):
    id: int
    created_at: datetime
    source_filename: Optional[str] = None
    source_type: str
    raw_text: str
    extracted: Dict[str, Any]
    flags: List[Dict[str, Any]]


class WhoMetricsOut(BaseModel):
    total_prescriptions: int
    total_drugs: int
    avg_drugs_per_prescription: float
    percent_generic: float
    percent_antibiotic_prescriptions: float
    percent_injection_prescriptions: float
    percent_eml: float
