# backend/database.py
"""
Database setup for Rx-Helper.

- Uses DATABASE_URL from env (defaults to sqlite file ./rxhelper.db for local/dev)
- Creates SQLAlchemy engine and session factory
- Provides Base for declarative models and get_db() dependency for FastAPI
- Handles SQLite special options and ensures directory exists when using a file path
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Prefer DeclarativeBase (SQLAlchemy 2.0); fallback to declarative_base for older installs
try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore
        pass
except Exception:
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()  # type: ignore

# ---------------- DATABASE URL ----------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rxhelper.db")

# If using SQLite file (sqlite:///./path/to/file.db) ensure directory exists
if DATABASE_URL.startswith("sqlite:///"):
    # extract the file path after the prefix
    sqlite_path = DATABASE_URL.replace("sqlite:///", "", 1)
    sqlite_dir = os.path.dirname(sqlite_path)
    if sqlite_dir and not os.path.exists(sqlite_dir):
        try:
            os.makedirs(sqlite_dir, exist_ok=True)
        except Exception:
            # best-effort; if this fails, the engine will still try to create the file
            pass

# SQLite needs special connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# ---------------- ENGINE ----------------
# Use future=True for SQLAlchemy 2.x behavior.
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

# ---------------- SESSION ----------------
# sessionmaker configured for modern SQLAlchemy:
# - autoflush disabled so you control flush points
# - expire_on_commit=False keeps objects usable after commit (optional)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)

# ---------------- DEPENDENCY ----------------
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy Session and closes it afterwards.

    Usage:

        from fastapi import Depends
        from .database import get_db

        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
