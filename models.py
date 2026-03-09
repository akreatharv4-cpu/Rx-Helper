# backend/models/prescription.py

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from typing import Any, Dict

# IMPORTANT: import Base from your database module
# If this model lives inside the same 'backend' package use the relative import:
from ..database import Base
# If you place this model at top-level and import directly, use:
# from backend.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # original uploaded filename (optional)
    source_filename = Column(String, nullable=True)

    # 'image' | 'pdf' | 'text' -- keep not nullable so we always know the source type
    source_type = Column(String, nullable=False)

    # full OCR/raw extracted text
    raw_text = Column(Text, nullable=False)

    # structured extracted data (medicines, doses, etc.)
    # Provide a Python-side default so SQLAlchemy sets {} for new rows
    extracted_json = Column(JSON, nullable=False, default=dict)

    # any flags / warnings detected (polypharmacy, red-flags)
    flags_json = Column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        fname = self.source_filename or ""
        return f"<Prescription id={self.id} source_type={self.source_type!r} filename={fname!r}>"
