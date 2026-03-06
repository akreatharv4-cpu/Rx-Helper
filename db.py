import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rxhelper.db")

# SQLite fix
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Engine
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base model
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder=".")

@app.route("/")
def home():
    return send_from_directory(".", "index.html")
