from datetime import date
from typing import Optional

from pydantic import BaseModel


class HabilidadeHeatmap(BaseModel):
    codigo: str
    descricao: str
    taxa_acerto: float
    prioridade: float
    ultima_pratica: Optional[date] = None


class PlanoTemporalResponse(BaseModel):
    semanas_f1: int
    semanas_f2: int
    semanas_f3: int
    semanas_f4: int
    carga_diaria_questoes: int


class EvolucaoNota(BaseModel):
    data: date
    nota_estimada: float
    nota_corte: float


class DashboardResponse(BaseModel):
    nota_estimada: float
    nota_corte: float
    total_simulados: int = 0
    total_redacoes: int = 0
    questoes_respondidas: int = 0
    taxa_acerto_geral: float = 0.0
    heatmap: list[HabilidadeHeatmap] = []
    plano_temporal: Optional[PlanoTemporalResponse] = None
    evolucao_notas: list[EvolucaoNota] = []
