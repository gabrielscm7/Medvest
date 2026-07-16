from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import Depends, HTTPException

from app.core.database import get_db, engine, Base
from app.models import *  # noqa: F401,F403
from app.routers import auth, flashcards, simulados, redacao, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Medvest API",
    description="Sistema Adaptativo de Preparação ENEM — Foco Medicina",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(simulados.router)
app.include_router(redacao.router)
app.include_router(dashboard.router)
app.include_router(flashcards.router)


@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


@app.get("/", tags=["System"])
def root():
    return {"message": "Bem-vindo à API Medvest!", "docs_url": "/docs"}
