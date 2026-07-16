import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno, Redacao
from app.schemas.redacao import CompetenciaNota, CorrecaoResponse, RedacaoResponse
from app.services.ai_provider.base import BaseAIProvider
from app.services.ai_provider.deepseek_provider import get_ai_provider
from app.services.ai_provider.fallback_ocr import get_fallback_provider
from app.services.ai_provider.qwen_provider import get_qwen_provider
from app.services.auth import get_aluno_atual

router = APIRouter(prefix="/api/redacoes", tags=["Redação"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _ai() -> BaseAIProvider:
    provider = get_ai_provider()
    if provider.api_key and provider.api_key != "your-deepseek-key-here":
        return provider
    return get_fallback_provider()


def _ocr() -> BaseAIProvider:
    qwen = get_qwen_provider()
    if qwen.api_key:
        return qwen
    return _ai()


@router.get("/", response_model=list[RedacaoResponse])
def listar_redacoes(
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    return (
        db.query(Redacao)
        .filter_by(aluno_id=aluno.id)
        .order_by(Redacao.criado_em.desc())
        .all()
    )


@router.post("/upload", response_model=RedacaoResponse, status_code=201)
async def upload_redacao(
    file: UploadFile = File(...),
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "png"
    nome = f"redacao_{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(UPLOAD_DIR, nome)

    image_bytes = await file.read()
    with open(caminho, "wb") as f:
        f.write(image_bytes)

    ocr = _ocr()
    texto_ocr = await ocr.ocr_image(image_bytes)

    redacao = Redacao(
        aluno_id=aluno.id,
        arquivo_path=caminho,
        texto_ocr=texto_ocr,
    )
    db.add(redacao)
    db.commit()
    db.refresh(redacao)
    return redacao


@router.post("/{redacao_id}/corrigir", response_model=CorrecaoResponse)
async def corrigir_redacao(
    redacao_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    redacao = (
        db.query(Redacao)
        .filter_by(id=redacao_id, aluno_id=aluno.id)
        .first()
    )
    if not redacao:
        raise HTTPException(status_code=404, detail="Redação não encontrada")

    ai = _ai()

    image_bytes = None
    if os.path.exists(redacao.arquivo_path):
        with open(redacao.arquivo_path, "rb") as f:
            image_bytes = f.read()

    resultado = await ai.correct_essay(redacao.texto_ocr or "", image_bytes)

    redacao.nota_c1 = resultado.get("nota_c1")
    redacao.nota_c2 = resultado.get("nota_c2")
    redacao.nota_c3 = resultado.get("nota_c3")
    redacao.nota_c4 = resultado.get("nota_c4")
    redacao.nota_c5 = resultado.get("nota_c5")
    redacao.nota_total = resultado.get("nota_total")
    redacao.feedback = resultado.get("feedback")
    db.commit()

    notas = []
    for i in range(1, 6):
        key = f"nota_c{i}"
        valor = resultado.get(key, 0)
        notas.append(CompetenciaNota(competencia=f"C{i}", nota=valor))

    return CorrecaoResponse(
        texto_ocr=redacao.texto_ocr or "",
        notas=notas,
        nota_total=resultado.get("nota_total", 0),
        feedback=resultado.get("feedback", ""),
    )


@router.get("/{redacao_id}", response_model=RedacaoResponse)
def obter_redacao(
    redacao_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    redacao = (
        db.query(Redacao)
        .filter_by(id=redacao_id, aluno_id=aluno.id)
        .first()
    )
    if not redacao:
        raise HTTPException(status_code=404, detail="Redação não encontrada")
    return redacao
