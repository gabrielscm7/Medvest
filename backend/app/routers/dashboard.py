from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    Aluno,
    Area,
    DominioHabilidade,
    Redacao,
    SimuladoUpload,
    QuestaoIdentificada,
)
from app.schemas.dashboard import DashboardResponse, PlanoTemporalResponse
from app.services.auth import get_aluno_atual
from app.services.prioritization import recalcular_prioridades
from app.services.temporal_planning import recalcular_macrociclo

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
def dashboard(
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    dominios = recalcular_prioridades(db, aluno.id)
    plano = recalcular_macrociclo(db, aluno)

    total_simulados = (
        db.query(SimuladoUpload)
        .filter_by(aluno_id=aluno.id)
        .count()
    )
    total_redacoes = (
        db.query(Redacao)
        .filter_by(aluno_id=aluno.id)
        .count()
    )
    questoes_respondidas = (
        db.query(QuestaoIdentificada)
        .join(QuestaoIdentificada.simulado_upload)
        .filter(SimuladoUpload.aluno_id == aluno.id)
        .count()
    )

    acertos = (
        db.query(QuestaoIdentificada)
        .join(QuestaoIdentificada.simulado_upload)
        .filter(
            SimuladoUpload.aluno_id == aluno.id,
            QuestaoIdentificada.acerto == True,
        )
        .count()
    )
    taxa_geral = (acertos / questoes_respondidas * 100) if questoes_respondidas > 0 else 0.0

    heatmap = []
    for d in dominios:
        heatmap.append(
            {
                "codigo": d.habilidade.codigo,
                "descricao": d.habilidade.descricao[:100],
                "taxa_acerto": d.taxa_acerto or 0,
                "prioridade": d.prioridade_calculada or 0,
                "ultima_pratica": d.ultima_pratica.date() if d.ultima_pratica else None,
            }
        )

    nota_media = 0.0
    redacoes = db.query(Redacao).filter_by(aluno_id=aluno.id).all()
    if redacoes:
        total_notas = sum(r.nota_total or 0 for r in redacoes)
        nota_media = total_notas / len(redacoes) / 1000.0 * 100

    return DashboardResponse(
        nota_estimada=round(max(taxa_geral, nota_media), 1),
        nota_corte=80.0,
        total_simulados=total_simulados,
        total_redacoes=total_redacoes,
        questoes_respondidas=questoes_respondidas,
        taxa_acerto_geral=round(taxa_geral, 1),
        heatmap=heatmap,
        plano_temporal=PlanoTemporalResponse(
            semanas_f1=plano.semanas_f1,
            semanas_f2=plano.semanas_f2,
            semanas_f3=plano.semanas_f3,
            semanas_f4=plano.semanas_f4,
            carga_diaria_questoes=plano.carga_diaria_questoes,
        ),
    )
