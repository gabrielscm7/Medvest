from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno, Flashcard, Habilidade
from app.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardRescheduleResponse,
    FlashcardResponse,
    FlashcardReview,
)
from app.services.ai_provider.base import BaseAIProvider
from app.services.ai_provider.deepseek_provider import get_ai_provider
from app.services.ai_provider.fallback_ocr import get_fallback_provider
from app.services.auth import get_aluno_atual
from app.services.flashcard_scheduler import agendar_revisao, get_flashcards_pendentes

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


def _ai() -> BaseAIProvider:
    provider = get_ai_provider()
    if provider.api_key and provider.api_key != "your-deepseek-key-here":
        return provider
    return get_fallback_provider()


@router.get("/pendentes", response_model=list[FlashcardResponse])
def listar_pendentes(
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    cards = get_flashcards_pendentes(db, aluno.id)
    return [
        {
            "id": c.id,
            "habilidade_id": c.habilidade_id,
            "habilidade_codigo": c.habilidade.codigo if c.habilidade else None,
            "pergunta": c.pergunta,
            "resposta": c.resposta,
            "fator_facilidade": c.fator_facilidade,
            "intervalo_dias": c.intervalo_dias,
            "proxima_revisao": c.proxima_revisao,
        }
        for c in cards
    ]


@router.post("/gerar", response_model=list[FlashcardResponse], status_code=201)
async def gerar_flashcards(
    body: FlashcardGenerateRequest,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    habilidade = db.get(Habilidade, body.habilidade_id)
    if not habilidade:
        raise HTTPException(status_code=404, detail="Habilidade não encontrada")

    ai = _ai()
    cards = []
    desc = habilidade.descricao

    for _ in range(body.quantidade):
        data = await ai.generate_flashcard(desc)
        card = Flashcard(
            aluno_id=aluno.id,
            habilidade_id=habilidade.id,
            pergunta=data["pergunta"],
            resposta=data["resposta"],
            proxima_revisao=date.today(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        cards.append(
            {
                "id": card.id,
                "habilidade_id": card.habilidade_id,
                "habilidade_codigo": habilidade.codigo,
                "pergunta": card.pergunta,
                "resposta": card.resposta,
                "fator_facilidade": card.fator_facilidade,
                "intervalo_dias": card.intervalo_dias,
                "proxima_revisao": card.proxima_revisao,
            }
        )

    return cards


@router.post("/{flashcard_id}/revisar", response_model=FlashcardRescheduleResponse)
def revisar_flashcard(
    flashcard_id: int,
    body: FlashcardReview,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    card = db.query(Flashcard).filter_by(id=flashcard_id, aluno_id=aluno.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard não encontrado")

    card = agendar_revisao(db, card, body.dificuldade)
    return FlashcardRescheduleResponse.model_validate(card)
