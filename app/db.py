from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Tenant

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caseledger.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.query(Tenant).filter(Tenant.api_key == "demo-key").first():
            db.add(Tenant(name="Demo Legal Operations", api_key="demo-key"))
            db.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
