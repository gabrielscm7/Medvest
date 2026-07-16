import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings as _settings


def _build_url():
    url = os.getenv("DATABASE_URL", "")
    if url and not url.startswith("${{"):
        return url
    host = os.getenv("PGHOST", "")
    if host:
        port = os.getenv("PGPORT", "5432")
        user = os.getenv("PGUSER", "postgres")
        password = os.getenv("PGPASSWORD", "")
        database = os.getenv("PGDATABASE", "medvest")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return "sqlite:///./medvest.db"


DATABASE_URL = _build_url()

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
