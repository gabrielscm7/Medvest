from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RedacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    texto_ocr: Optional[str] = None
    nota_c1: Optional[int] = None
    nota_c2: Optional[int] = None
    nota_c3: Optional[int] = None
    nota_c4: Optional[int] = None
    nota_c5: Optional[int] = None
    nota_total: Optional[int] = None
    feedback: Optional[str] = None
    criado_em: datetime


class CompetenciaNota(BaseModel):
    competencia: str
    nota: int
    maximo: int = 200


class CorrecaoResponse(BaseModel):
    texto_ocr: str
    notas: list[CompetenciaNota]
    nota_total: int
    feedback: str
