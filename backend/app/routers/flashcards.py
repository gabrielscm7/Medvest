from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno, Flashcard, Habilidade, QuestaoIdentificada, SimuladoUpload
from app.schemas.flashcard import (
    FlashcardFromErrorsRequest,
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

router = APIRouter(prefix="/api/flashcards", tags=["Flashcards"])


def _get_wrong_questions(db: Session, aluno_id: int, simulado_id: Optional[int] = None, limite: int = 10) -> list[QuestaoIdentificada]:
    query = (
        db.query(QuestaoIdentificada)
        .join(SimuladoUpload)
        .filter(
            SimuladoUpload.aluno_id == aluno_id,
            QuestaoIdentificada.acerto == False,
            QuestaoIdentificada.texto_questao.isnot(None),
            QuestaoIdentificada.resposta_correta.isnot(None),
        )
    )
    if simulado_id:
        query = query.filter(QuestaoIdentificada.simulado_upload_id == simulado_id)
    return query.order_by(QuestaoIdentificada.numero_questao).limit(limite).all()


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


@router.post("/gerar-de-erros", response_model=list[FlashcardResponse], status_code=201)
async def gerar_flashcards_de_erros(
    body: FlashcardFromErrorsRequest,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    questoes_erradas = _get_wrong_questions(db, aluno.id, body.simulado_id, body.quantidade)
    if not questoes_erradas:
        raise HTTPException(status_code=404, detail="Nenhuma questão errada encontrada com texto extraído")

    ai = _ai()
    cards = []

    for q in questoes_erradas:
        prompt = (
            "Com base na questão do ENEM abaixo e na resposta correta, "
            "gere um flashcard no estilo pergunta/resposta para revisão.\n"
            "A PERGUNTA do flashcard deve ser uma versão resumida da questão ou o conceito cobrado.\n"
            "A RESPOSTA deve explicar por que a alternativa correta é a certa.\n\n"
            f"Questão: {q.texto_questao}\n"
            f"Resposta correta: {q.resposta_correta}\n\n"
            "Retorne JSON: {\"pergunta\": \"...\", \"resposta\": \"...\"}"
        )
        try:
            client = ai._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": ai.model,
                    "messages": [
                        {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            import json as _json
            data = _json.loads(result)
        except Exception:
            continue

        habilidade_id = q.habilidade_id or 1
        card = Flashcard(
            aluno_id=aluno.id,
            habilidade_id=habilidade_id,
            pergunta=data.get("pergunta", q.texto_questao[:100]),
            resposta=data.get("resposta", f"Resposta correta: {q.resposta_correta}"),
            proxima_revisao=date.today(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        cards.append({
            "id": card.id,
            "habilidade_id": card.habilidade_id,
            "habilidade_codigo": q.habilidade.codigo if q.habilidade else None,
            "pergunta": card.pergunta,
            "resposta": card.resposta,
            "fator_facilidade": card.fator_facilidade,
            "intervalo_dias": card.intervalo_dias,
            "proxima_revisao": card.proxima_revisao,
        })

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
