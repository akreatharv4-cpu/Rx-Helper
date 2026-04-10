from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func

from database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    source_filename = Column(String, nullable=True)
    source_type = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)

    extracted_json = Column(JSON, nullable=False, default=dict)
    flags_json = Column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        fname = self.source_filename or ""
        return f"<Prescription id={self.id} source_type={self.source_type!r} filename={fname!r}>"