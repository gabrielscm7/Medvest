from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SimuladoUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    total_questoes_detectado: Optional[int] = None
    alternativas_por_questao: Optional[int] = None
    processado: bool = False
    criado_em: datetime


class QuestaoGabarito(BaseModel):
    numero_questao: int
    resposta_aluno: Optional[str] = None
    resposta_correta: Optional[str] = None


class GabaritoPreenchimento(BaseModel):
    questoes: list[QuestaoGabarito]


class DeteccaoResponse(BaseModel):
    total_questoes: int
    alternativas_por_questao: int
    numeracao_inicial: int = 1
    questoes: list[QuestaoGabarito]


class QuestaoIdentificadaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_questao: int
    habilidade_codigo: Optional[str] = None
    tema_livre: Optional[str] = None
    dificuldade_estimada: Optional[float] = None
    texto_questao: Optional[str] = None
    resposta_aluno: Optional[str] = None
    resposta_correta: Optional[str] = None
    acerto: Optional[bool] = None
    classificacao_confirmada_manualmente: bool = False


class ClassificacaoOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_questao: int
    habilidade_codigo: Optional[str] = None
    tema_livre: Optional[str] = None
    dificuldade_estimada: Optional[float] = None
    texto_questao: Optional[str] = None
    classificacao_confirmada_manualmente: bool = False


class ClassificarResponse(BaseModel):
    questoes: list[ClassificacaoOutput]


class HabilidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    descricao: str


class SimuladoCompletoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    total_questoes_detectado: Optional[int] = None
    criado_em: datetime
    questoes: list[QuestaoIdentificadaResponse] = []
