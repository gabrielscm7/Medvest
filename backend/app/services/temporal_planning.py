from datetime import date

from sqlalchemy.orm import Session

from app.models import Aluno, PlanoTemporal

DATA_PROVA_DIA1 = date(2026, 11, 8)


def recalcular_macrociclo(db: Session, aluno: Aluno) -> PlanoTemporal:
    dias = (DATA_PROVA_DIA1 - date.today()).days
    semanas_totais = max(dias // 7, 1)
    nivel = _media_taxa_acerto(db, aluno.id)

    if nivel < 0.4:
        distrib = {"F1": 0.45, "F2": 0.30, "F3": 0.20, "F4": 0.05}
        carga = 35
    elif nivel < 0.65:
        distrib = {"F1": 0.30, "F2": 0.35, "F3": 0.25, "F4": 0.10}
        carga = 25
    else:
        distrib = {"F1": 0.10, "F2": 0.30, "F3": 0.40, "F4": 0.20}
        carga = 20

    plano = db.query(PlanoTemporal).filter_by(aluno_id=aluno.id).first()
    if not plano:
        plano = PlanoTemporal(aluno_id=aluno.id)
        db.add(plano)

    plano.semanas_f1 = max(1, round(distrib["F1"] * semanas_totais))
    plano.semanas_f2 = max(1, round(distrib["F2"] * semanas_totais))
    plano.semanas_f3 = max(1, round(distrib["F3"] * semanas_totais))
    plano.semanas_f4 = max(1, round(distrib["F4"] * semanas_totais))
    plano.carga_diaria_questoes = carga

    db.commit()
    db.refresh(plano)
    return plano


def _media_taxa_acerto(db: Session, aluno_id: int) -> float:
    from app.models import DominioHabilidade

    dominios = (
        db.query(DominioHabilidade)
        .filter_by(aluno_id=aluno_id)
        .all()
    )
    if not dominios:
        return 0.0
    return sum(d.taxa_acerto or 0 for d in dominios) / len(dominios)
