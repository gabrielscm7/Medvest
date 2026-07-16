import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno, QuestaoIdentificada, SimuladoUpload
from app.schemas.simulado import (
    DeteccaoResponse,
    GabaritoPreenchimento,
    QuestaoGabarito,
    QuestaoIdentificadaResponse,
    SimuladoCompletoResponse,
    SimuladoUploadResponse,
)
from app.services.ai_provider.base import BaseAIProvider
from app.services.ai_provider.deepseek_provider import get_ai_provider
from app.services.ai_provider.fallback_ocr import get_fallback_provider
from app.services.auth import get_aluno_atual

router = APIRouter(prefix="/simulados", tags=["Simulados"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ai() -> BaseAIProvider:
    provider = get_ai_provider()
    if provider.api_key and provider.api_key != "your-deepseek-key-here":
        return provider
    return get_fallback_provider()


@router.get("/", response_model=list[SimuladoUploadResponse])
def listar_simulados(
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    return (
        db.query(SimuladoUpload)
        .filter_by(aluno_id=aluno.id)
        .order_by(SimuladoUpload.criado_em.desc())
        .all()
    )


@router.post("/upload", response_model=SimuladoUploadResponse, status_code=201)
async def upload_simulado(
    file: UploadFile = File(...),
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "png"
    nome = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(UPLOAD_DIR, nome)

    image_bytes = await file.read()
    with open(caminho, "wb") as f:
        f.write(image_bytes)

    simulado = SimuladoUpload(
        aluno_id=aluno.id,
        arquivo_path=caminho,
        tipo="caderno_prova",
    )
    db.add(simulado)
    db.commit()
    db.refresh(simulado)
    return simulado


@router.post("/{simulado_id}/detectar", response_model=DeteccaoResponse)
async def detectar_estrutura(
    simulado_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    simulado = (
        db.query(SimuladoUpload)
        .filter_by(id=simulado_id, aluno_id=aluno.id)
        .first()
    )
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    with open(simulado.arquivo_path, "rb") as f:
        image_bytes = f.read()

    ai = _ai()
    estrutura = await ai.detect_exam_structure(image_bytes)

    simulado.total_questoes_detectado = estrutura.get("total_questoes", 45)
    simulado.alternativas_por_questao = estrutura.get("alternativas_por_questao", 5)
    db.commit()

    inicio = estrutura.get("numeracao_inicial", 1)
    questoes = []
    for i in range(estrutura.get("total_questoes", 45)):
        questoes.append(
            QuestaoGabarito(
                numero_questao=inicio + i,
            )
        )

    return DeteccaoResponse(
        total_questoes=estrutura.get("total_questoes", 45),
        alternativas_por_questao=estrutura.get("alternativas_por_questao", 5),
        numeracao_inicial=inicio,
        questoes=questoes,
    )


@router.put("/{simulado_id}/gabarito", response_model=SimuladoCompletoResponse)
def preencher_gabarito(
    simulado_id: int,
    body: GabaritoPreenchimento,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    simulado = (
        db.query(SimuladoUpload)
        .filter_by(id=simulado_id, aluno_id=aluno.id)
        .first()
    )
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    for q in body.questoes:
        existing = (
            db.query(QuestaoIdentificada)
            .filter_by(simulado_upload_id=simulado_id, numero_questao=q.numero_questao)
            .first()
        )
        if existing:
            existing.resposta_aluno = q.resposta_aluno
            existing.resposta_correta = q.resposta_correta
            if q.resposta_aluno and q.resposta_correta:
                existing.acerto = q.resposta_aluno.strip().upper() == q.resposta_correta.strip().upper()
        else:
            acerto = None
            if q.resposta_aluno and q.resposta_correta:
                acerto = q.resposta_aluno.strip().upper() == q.resposta_correta.strip().upper()
            db.add(
                QuestaoIdentificada(
                    simulado_upload_id=simulado_id,
                    numero_questao=q.numero_questao,
                    resposta_aluno=q.resposta_aluno,
                    resposta_correta=q.resposta_correta,
                    acerto=acerto,
                )
            )

    simulado.processado = True
    db.commit()

    questoes_db = (
        db.query(QuestaoIdentificada)
        .filter_by(simulado_upload_id=simulado_id)
        .order_by(QuestaoIdentificada.numero_questao)
        .all()
    )

    return SimuladoCompletoResponse(
        id=simulado.id,
        tipo=simulado.tipo,
        total_questoes_detectado=simulado.total_questoes_detectado,
        criado_em=simulado.criado_em,
        questoes=[
            QuestaoIdentificadaResponse(
                id=q.id,
                numero_questao=q.numero_questao,
                resposta_aluno=q.resposta_aluno,
                resposta_correta=q.resposta_correta,
                acerto=q.acerto,
            )
            for q in questoes_db
        ],
    )


@router.get("/{simulado_id}", response_model=SimuladoCompletoResponse)
def obter_simulado(
    simulado_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    simulado = (
        db.query(SimuladoUpload)
        .filter_by(id=simulado_id, aluno_id=aluno.id)
        .first()
    )
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    questoes_db = (
        db.query(QuestaoIdentificada)
        .filter_by(simulado_upload_id=simulado_id)
        .order_by(QuestaoIdentificada.numero_questao)
        .all()
    )

    return SimuladoCompletoResponse(
        id=simulado.id,
        tipo=simulado.tipo,
        total_questoes_detectado=simulado.total_questoes_detectado,
        criado_em=simulado.criado_em,
        questoes=[
            QuestaoIdentificadaResponse(
                id=q.id,
                numero_questao=q.numero_questao,
                habilidade_codigo=q.habilidade.codigo if q.habilidade else None,
                tema_livre=q.tema_livre,
                dificuldade_estimada=q.dificuldade_estimada,
                resposta_aluno=q.resposta_aluno,
                resposta_correta=q.resposta_correta,
                acerto=q.acerto,
                classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
            )
            for q in questoes_db
        ],
    )
