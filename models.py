from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from .db import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    source_filename = Column(String, nullable=True)

    source_type = Column(
        String,
        nullable=False
    )  # image / pdf / text

    raw_text = Column(
        Text,
        nullable=False
    )

    extracted_json = Column(
        JSON,
        nullable=False
    )

    flags_json = Column(
        JSON,
        nullable=False
    )
