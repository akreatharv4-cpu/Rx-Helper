from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from .db import Base

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_filename = Column(String, nullable=True)
    source_type = Column(String, nullable=False)  # image/pdf/text
    raw_text = Column(Text, nullable=False)

    extracted_json = Column(Text, nullable=False)  # JSON string
    flags_json = Column(Text, nullable=False)      # JSON string
