from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    Aluno,
    Area,
    Competencia,
    DominioHabilidade,
    Habilidade,
    Redacao,
    SimuladoUpload,
    QuestaoIdentificada,
)
from app.schemas.dashboard import (
    AreaChartData,
    CompetenciaChartData,
    DashboardResponse,
    PlanoTemporalResponse,
    TemaChartData,
)
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

    areas = db.query(Area).all()
    graficos_area = []
    for area in areas:
        questoes_area = (
            db.query(QuestaoIdentificada)
            .join(QuestaoIdentificada.simulado_upload)
            .join(QuestaoIdentificada.habilidade)
            .join(Habilidade.competencia)
            .filter(
                SimuladoUpload.aluno_id == aluno.id,
                Competencia.area_id == area.id,
                QuestaoIdentificada.acerto.isnot(None),
            )
            .all()
        )
        total = len(questoes_area)
        acertos_count = sum(1 for q in questoes_area if q.acerto)
        taxa = acertos_count / total if total > 0 else 0.0
        graficos_area.append(AreaChartData(
            nome=area.nome,
            taxa_acerto=round(taxa, 2),
            peso_medicina=float(area.peso_medicina),
            total_questoes=total,
        ))

    graficos_competencia = []
    for area in areas:
        for comp in area.competencias:
            questoes_comp = (
                db.query(QuestaoIdentificada)
                .join(QuestaoIdentificada.simulado_upload)
                .join(QuestaoIdentificada.habilidade)
                .filter(
                    SimuladoUpload.aluno_id == aluno.id,
                    Habilidade.competencia_id == comp.id,
                    QuestaoIdentificada.acerto.isnot(None),
                )
                .all()
            )
            total = len(questoes_comp)
            acertos_count = sum(1 for q in questoes_comp if q.acerto)
            taxa = acertos_count / total if total > 0 else 0.0
            graficos_competencia.append(CompetenciaChartData(
                area_nome=area.nome,
                competencia_numero=comp.numero,
                descricao=comp.descricao[:80],
                taxa_acerto=round(taxa, 2),
                total_questoes=total,
            ))

    temas_counts: dict[str, dict] = {}
    questoes_com_tema = (
        db.query(QuestaoIdentificada)
        .join(QuestaoIdentificada.simulado_upload)
        .filter(
            SimuladoUpload.aluno_id == aluno.id,
            QuestaoIdentificada.tema_livre.isnot(None),
            QuestaoIdentificada.acerto.isnot(None),
        )
        .all()
    )
    for q in questoes_com_tema:
        tema = q.tema_livre or "sem tema"
        if tema not in temas_counts:
            temas_counts[tema] = {"total": 0, "acertos": 0, "area": ""}
        temas_counts[tema]["total"] += 1
        if q.acerto:
            temas_counts[tema]["acertos"] += 1
        if q.habilidade and q.habilidade.competencia and q.habilidade.competencia.area:
            temas_counts[tema]["area"] = q.habilidade.competencia.area.nome

    graficos_tema = [
        TemaChartData(
            tema=tema,
            area_nome=data["area"],
            taxa_acerto=round(data["acertos"] / data["total"], 2) if data["total"] > 0 else 0.0,
            total_questoes=data["total"],
        )
        for tema, data in sorted(temas_counts.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

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
        graficos_area=graficos_area,
        graficos_competencia=graficos_competencia,
        graficos_tema=graficos_tema,
    )
