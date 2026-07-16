import json
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno, Area, Competencia, Habilidade, QuestaoIdentificada, SimuladoUpload
from app.schemas.simulado import (
    ClassificacaoOutput,
    ClassificarResponse,
    DeteccaoResponse,
    GabaritoPreenchimento,
    HabilidadeResponse,
    QuestaoGabarito,
    QuestaoIdentificadaResponse,
    SimuladoCompletoResponse,
    SimuladoDeleteResponse,
    SimuladoUpdateRequest,
    SimuladoUploadResponse,
)
from app.services.ai_provider.base import BaseAIProvider
from app.services.ai_provider.deepseek_provider import DeepSeekProvider, get_ai_provider
from app.services.ai_provider.fallback_ocr import get_fallback_provider
from app.services.auth import get_aluno_atual
from app.services.prioritization import recalcular_prioridades

router = APIRouter(prefix="/api/simulados", tags=["Simulados"])

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

    recalcular_prioridades(db, aluno.id)

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


@router.get("/habilidades", response_model=list[HabilidadeResponse])
def listar_habilidades(db: Session = Depends(get_db)):
    return db.query(Habilidade).order_by(Habilidade.codigo).all()


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
                texto_questao=q.texto_questao,
                resposta_aluno=q.resposta_aluno,
                resposta_correta=q.resposta_correta,
                acerto=q.acerto,
                classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
            )
            for q in questoes_db
        ],
    )


@router.delete("/{simulado_id}", response_model=SimuladoDeleteResponse)
def deletar_simulado(
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

    if os.path.exists(simulado.arquivo_path):
        os.remove(simulado.arquivo_path)

    db.delete(simulado)
    db.commit()
    return SimuladoDeleteResponse()


@router.put("/{simulado_id}", response_model=SimuladoUploadResponse)
def atualizar_simulado(
    simulado_id: int,
    body: SimuladoUpdateRequest,
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

    if body.tipo is not None:
        simulado.tipo = body.tipo
    db.commit()
    db.refresh(simulado)
    return simulado


@router.post("/{simulado_id}/extrair-texto", response_model=ClassificarResponse)
async def extrair_texto_questoes(
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

    import base64
    b64 = base64.b64encode(image_bytes).decode()

    ai = _ai()
    is_deepseek = isinstance(ai, DeepSeekProvider)

    if is_deepseek:
        import json as _json
        client = ai._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": ai.model,
                "messages": [
                    {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": (
                                "Analise esta imagem de prova ENEM. Identifique CADA questão "
                                "individualmente e extraia o texto completo de cada uma. "
                                "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
                                '{"numero": <número>, "texto": "<texto completo>"}\n\n'
                                "Extraia TODAS as questões visíveis. Responda apenas o JSON, sem explicações."
                            )},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Erro da API DeepSeek: {response.text}")
        raw = response.json()["choices"][0]["message"]["content"]
        questoes_texto = _json.loads(raw)
        if isinstance(questoes_texto, dict) and "questoes" in questoes_texto:
            questoes_texto = questoes_texto["questoes"]
    else:
        from app.services.ai_provider.fallback_ocr import _FALLBACK_QUESTIONS
        questoes_texto = _FALLBACK_QUESTIONS

    resp = []
    for item in questoes_texto:
        num = int(item.get("numero", 0))
        texto = item.get("texto", "")
        if not num:
            continue
        questao = (
            db.query(QuestaoIdentificada)
            .filter_by(simulado_upload_id=simulado_id, numero_questao=num)
            .first()
        )
        if questao:
            questao.texto_questao = texto
        else:
            questao = QuestaoIdentificada(
                simulado_upload_id=simulado_id,
                numero_questao=num,
                texto_questao=texto,
            )
            db.add(questao)
        resp.append(questao)

    db.commit()
    return ClassificarResponse(
        questoes=[
            ClassificacaoOutput(
                id=q.id,
                numero_questao=q.numero_questao,
                texto_questao=q.texto_questao,
                classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
            )
            for q in resp
        ]
    )


@router.post("/{simulado_id}/classificar", response_model=ClassificarResponse)
async def classificar_questoes(
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

    questoes = (
        db.query(QuestaoIdentificada)
        .filter_by(simulado_upload_id=simulado_id)
        .all()
    )

    with open(simulado.arquivo_path, "rb") as f:
        image_bytes = f.read()

    ai = _ai()

    for q in questoes:
        texto = q.texto_questao or ""
        if not texto.strip():
            continue

        try:
            result = await ai.classify_question(texto, image_bytes)
        except Exception:
            continue

        habilidade_codigo = result.get("habilidade", "")
        tema_livre = result.get("tema_livre", "")
        dificuldade_raw = result.get("dificuldade", "media")

        dificuldade_map = {"facil": 1.0, "media": 2.0, "dificil": 3.0}
        q.dificuldade_estimada = dificuldade_map.get(dificuldade_raw, 2.0)
        q.tema_livre = tema_livre

        if habilidade_codigo:
            area_nome = result.get("area", "")
            query = db.query(Habilidade).filter(Habilidade.codigo == habilidade_codigo)
            if area_nome:
                query = query.join(Competencia).join(Area).filter(Area.nome == area_nome)
            habilidade = query.first()
            if habilidade:
                q.habilidade_id = habilidade.id

    db.commit()
    recalcular_prioridades(db, aluno.id)

    return ClassificarResponse(
        questoes=[
            ClassificacaoOutput(
                id=q.id,
                numero_questao=q.numero_questao,
                habilidade_codigo=q.habilidade.codigo if q.habilidade else None,
                tema_livre=q.tema_livre,
                dificuldade_estimada=q.dificuldade_estimada,
                texto_questao=q.texto_questao,
                classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
            )
            for q in questoes
        ]
    )
