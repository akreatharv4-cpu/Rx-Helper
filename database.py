# backend/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from typing import Generator

# ---------------- DATABASE URL ----------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rxhelper.db")

# SQLite needs special argument
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# ---------------- ENGINE ----------------

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

# ---------------- SESSION ----------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# ---------------- BASE MODEL ----------------

class Base(DeclarativeBase):
    pass

# ---------------- DEPENDENCY ----------------

def get_db() -> Generator[Session, None, None]:

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
