from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class AlunoBase(BaseModel):
    nome: str
    email: EmailStr
    data_prova_dia1: date = date(2026, 11, 8)
    data_prova_dia2: date = date(2026, 11, 15)
    meta_instituicao: Optional[str] = None


class AlunoCreate(AlunoBase):
    senha: str


class AlunoUpdate(BaseModel):
    nome: Optional[str] = None
    meta_instituicao: Optional[str] = None
    data_prova_dia1: Optional[date] = None
    data_prova_dia2: Optional[date] = None


class AlunoResponse(AlunoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime


class BemEstarCreate(BaseModel):
    data: date
    sono: str
    energia: str


class BemEstarResponse(BemEstarCreate):
    model_config = ConfigDict(from_attributes=True)
