from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models import Flashcard


def agendar_revisao(db: Session, flashcard: Flashcard, dificuldade: str) -> Flashcard:
    mapa = {"facil": 0, "medio": 1, "dificil": 2}
    q = mapa.get(dificuldade, 1)
    ff = float(flashcard.fator_facilidade or 2.5)

    if q > 1:
        ff = max(1.3, ff - 0.2)
        flashcard.intervalo_dias = 1
    else:
        ff = ff + (0.1 * (1 - q))
        flashcard.intervalo_dias = max(1, int(flashcard.intervalo_dias * ff))

    flashcard.fator_facilidade = ff

    flashcard.proxima_revisao = date.today() + timedelta(days=flashcard.intervalo_dias)
    db.commit()
    db.refresh(flashcard)
    return flashcard


def get_flashcards_pendentes(db: Session, aluno_id: int, limite: int = 10):
    hoje = date.today()
    return (
        db.query(Flashcard)
        .filter(
            Flashcard.aluno_id == aluno_id,
            Flashcard.proxima_revisao <= hoje,
        )
        .order_by(Flashcard.proxima_revisao.asc())
        .limit(limite)
        .all()
    )
