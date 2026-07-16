from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Area, DominioHabilidade, Habilidade, QuestaoIdentificada


def recalcular_prioridades(db: Session, aluno_id: int) -> list[DominioHabilidade]:
    habilidades = db.query(Habilidade).join(Habilidade.competencia).all()

    for h in habilidades:
        dominio = (
            db.query(DominioHabilidade)
            .filter_by(aluno_id=aluno_id, habilidade_id=h.id)
            .first()
        )
        if not dominio:
            dominio = DominioHabilidade(
                aluno_id=aluno_id,
                habilidade_id=h.id,
                taxa_acerto=0.0,
                prioridade_calculada=0.0,
            )
            db.add(dominio)

        taxa = dominio.taxa_acerto or 0.0

        dias_sem_pratica = 0.0
        if dominio.ultima_pratica:
            delta = (date.today() - dominio.ultima_pratica.date()).days
            dias_sem_pratica = float(delta)
        fator_recencia = min(dias_sem_pratica / 14.0, 2.0)

        peso = h.competencia.area.peso_medicina or 1.0
        incidencia = _calcular_incidencia_historica(db, aluno_id, h.id)

        prioridade = peso * (1.0 - taxa) * fator_recencia * (1.0 + incidencia)
        dominio.prioridade_calculada = round(prioridade, 4)

    db.commit()
    return (
        db.query(DominioHabilidade)
        .filter_by(aluno_id=aluno_id)
        .order_by(DominioHabilidade.prioridade_calculada.desc())
        .all()
    )


def _calcular_incidencia_historica(db: Session, aluno_id: int, habilidade_id: int) -> float:
    questoes = (
        db.query(QuestaoIdentificada)
        .join(QuestaoIdentificada.simulado)
        .filter(
            QuestaoIdentificada.simulado.has(aluno_id=aluno_id),
            QuestaoIdentificada.habilidade_id == habilidade_id,
        )
        .count()
    )
    return min(questoes / 50.0, 1.0)


def get_habilidades_prioritarias(db: Session, aluno_id: int, limite: int = 5):
    dominios = (
        db.query(DominioHabilidade)
        .filter_by(aluno_id=aluno_id)
        .order_by(DominioHabilidade.prioridade_calculada.desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "habilidade_codigo": d.habilidade.codigo,
            "descricao": d.habilidade.descricao,
            "taxa_acerto": d.taxa_acerto,
            "prioridade": d.prioridade_calculada,
        }
        for d in dominios
    ]
