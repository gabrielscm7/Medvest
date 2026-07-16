from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FlashcardGenerateRequest(BaseModel):
    habilidade_id: int
    quantidade: int = 3


class FlashcardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habilidade_id: int
    habilidade_codigo: Optional[str] = None
    pergunta: str
    resposta: str
    fator_facilidade: float = 2.5
    intervalo_dias: int = 1
    proxima_revisao: Optional[date] = None


class FlashcardReview(BaseModel):
    dificuldade: str


class FlashcardRescheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervalo_dias: int
    proxima_revisao: date
    fator_facilidade: float
