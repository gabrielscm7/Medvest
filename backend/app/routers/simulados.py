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
    GabaritoExtraidoResponse,
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
from app.services.ai_provider.qwen_provider import QwenProvider, get_qwen_provider
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


def _check_vision() -> None:
    if not get_qwen_provider().api_key:
        raise HTTPException(
            status_code=400,
            detail="Análise de imagens requer QWEN_API_KEY configurada. O modelo DeepSeek não suporta imagens.",
        )


def _is_pdf(path: str) -> bool:
    return path.lower().endswith(".pdf")

def _is_image(path: str) -> bool:
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"))


def _convert_pdf_to_markdown(path: str) -> str:
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(path)
    return result.text_content


def _parse_questions_from_md(md_text: str) -> list[dict]:
    import re
    questions = []
    pattern = r'(?:^|\n)(?:\#+\s*)?(?:Questão\s*)?(\d+)[\.\):]?\s*\n?(.*?)(?=\n(?:\#+\s*)?(?:Questão\s*)?\d+[\.\):]?\s|\Z)'
    matches = re.findall(pattern, md_text, re.DOTALL | re.MULTILINE)
    for num, texto in matches:
        texto = texto.strip()
        if texto:
            questions.append({"numero": int(num), "texto": texto})
    if not questions:
        pattern2 = r'(?:^|\n)(\d+)[\.\):]\s+(.*?)(?=\n\d+[\.\):]\s|\Z)'
        matches2 = re.findall(pattern2, md_text, re.DOTALL | re.MULTILINE)
        for num, texto in matches2:
            texto = texto.strip()
            if texto:
                questions.append({"numero": int(num), "texto": texto})
    return questions


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
    try:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    except Exception:
        ext = ""
    if ext in ("pdf",):
        tipo_real = "pdf"
    elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
        tipo_real = "imagem"
    else:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não suportado: {ext}")

    nome = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(UPLOAD_DIR, nome)

    image_bytes = await file.read()
    with open(caminho, "wb") as f:
        f.write(image_bytes)

    simulado = SimuladoUpload(
        aluno_id=aluno.id,
        arquivo_path=caminho,
        tipo=tipo_real,
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

    if not os.path.exists(simulado.arquivo_path):
        raise HTTPException(
            status_code=404,
            detail="Arquivo do simulado não encontrado no servidor. Faça o upload novamente.",
        )

    try:
        qwen = get_qwen_provider()
        if _is_pdf(simulado.arquivo_path):
            md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
            ai = _ai()
            if ai.api_key and ai.api_key != "your-deepseek-key-here":
                prompt = (
                    "Analise o texto abaixo extraído de um PDF de prova ENEM e determine:\n"
                    "- Quantidade total de questões\n"
                    "- Número de alternativas por questão (4 ou 5)\n"
                    "- Numeração inicial\n"
                    "Retorne JSON: {\"total_questoes\": N, \"alternativas_por_questao\": N, \"numeracao_inicial\": N}\n\n"
                    f"Texto:\n{md_text[:8000]}"
                )
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
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
                import json as _json
                estrutura = _json.loads(raw)
            else:
                estrutura = {"total_questoes": 90, "alternativas_por_questao": 5, "numeracao_inicial": 1}
        elif qwen.api_key:
            with open(simulado.arquivo_path, "rb") as f:
                image_bytes = f.read()
            estrutura = await qwen.detect_exam_structure(image_bytes)
        else:
            raise HTTPException(
                status_code=400,
                detail="Detecção em imagens requer QWEN_API_KEY configurada. Para PDFs, a detecção funciona normalmente.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha na detecção via IA: {str(e)}")

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

    if not os.path.exists(simulado.arquivo_path):
        raise HTTPException(
            status_code=404,
            detail="Arquivo do simulado não encontrado no servidor. Faça o upload novamente.",
        )

    ai = _ai()
    is_deepseek = isinstance(ai, DeepSeekProvider)

    if not is_deepseek:
        from app.services.ai_provider.fallback_ocr import _FALLBACK_QUESTIONS
        questoes_texto = _FALLBACK_QUESTIONS
    else:
        if _is_pdf(simulado.arquivo_path):
            md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
            questoes_texto = _parse_questions_from_md(md_text)
            if not questoes_texto:
                prompt = (
                    "Analise este texto de prova ENEM extraído de um PDF. "
                    "Identifique CADA questão individualmente e extraia o texto completo de cada uma. "
                    "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
                    '{"numero": <número>, "texto": "<texto completo>"}\n\n'
                    "Extraia TODAS as questões. Responda apenas o JSON, sem explicações.\n\n"
                    f"Texto:\n{md_text[:16000]}"
                )
                client = ai._get_client()
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": ai.model,
                        "messages": [
                            {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 8192,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Erro da API DeepSeek: {response.text}")
                raw = response.json()["choices"][0]["message"]["content"]
                import json as _json
                questoes_texto = _json.loads(raw)
                if isinstance(questoes_texto, dict) and "questoes" in questoes_texto:
                    questoes_texto = questoes_texto["questoes"]
        else:
            _check_vision()
            import base64
            with open(simulado.arquivo_path, "rb") as f:
                image_bytes = f.read()

            qwen = get_qwen_provider()
            ocr_text = await qwen.ocr_image(image_bytes)

            prompt = (
                "Analise o texto abaixo extraído de uma prova ENEM via OCR. "
                "Identifique CADA questão individualmente e extraia o texto completo de cada uma. "
                "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
                '{"numero": <número>, "texto": "<texto completo>"}\n\n'
                "Extraia TODAS as questões. Responda apenas o JSON, sem explicações.\n\n"
                f"Texto OCR:\n{ocr_text}"
            )
            client = ai._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": ai.model,
                    "messages": [
                        {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8192,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Erro da API DeepSeek: {response.text}")
            raw = response.json()["choices"][0]["message"]["content"]
            import json as _json
            questoes_texto = _json.loads(raw)
            if isinstance(questoes_texto, dict) and "questoes" in questoes_texto:
                questoes_texto = questoes_texto["questoes"]

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

    if not os.path.exists(simulado.arquivo_path):
        raise HTTPException(
            status_code=404,
            detail="Arquivo do simulado não encontrado no servidor. Faça o upload novamente.",
        )

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


@router.post("/{simulado_id}/extrair-gabarito", response_model=GabaritoExtraidoResponse)
async def extrair_gabarito(
    simulado_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    simulado = db.query(SimuladoUpload).filter_by(id=simulado_id, aluno_id=aluno.id).first()
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    questoes_db = (
        db.query(QuestaoIdentificada)
        .filter_by(simulado_upload_id=simulado_id)
        .order_by(QuestaoIdentificada.numero_questao)
        .all()
    )

    if not os.path.exists(simulado.arquivo_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    questoes_extraidas = []

    ai = _ai()
    is_deepseek = isinstance(ai, DeepSeekProvider)

    if _is_pdf(simulado.arquivo_path):
        md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
        if is_deepseek:
            tail = md_text[-4000:] if len(md_text) > 4000 else md_text
            prompt = (
                "Extraia o GABARITO (respostas corretas) do texto abaixo. "
                "O gabarito lista o número da questão e a alternativa correta "
                "(ex: '01 - A', '02 - C', '1:A', '2:B', etc). "
                "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
                '{"numero_questao": <número>, "resposta_correta": "<letra>"}\n\n'
                f"Texto:\n{tail}"
            )
            try:
                response = await ai._call_raw({
                    "model": ai.model,
                    "messages": [
                        {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                })
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
                import json as _json
                data = _json.loads(raw)
                if isinstance(data, dict):
                    questoes_extraidas = data.get("questoes", data.get("gabarito", []))
                else:
                    questoes_extraidas = data
            except Exception:
                questoes_extraidas = []
    elif _is_image(simulado.arquivo_path):
        _check_vision()
        with open(simulado.arquivo_path, "rb") as f:
            image_bytes = f.read()
        qwen = get_qwen_provider()
        ocr_text = await qwen.ocr_image(image_bytes)
        if is_deepseek:
            prompt = (
                "Extraia o GABARITO (respostas corretas) do texto OCR abaixo. "
                "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
                '{"numero_questao": <número>, "resposta_correta": "<letra>"}\n\n'
                f"Texto OCR:\n{ocr_text}"
            )
            try:
                response = await ai._call_raw({
                    "model": ai.model,
                    "messages": [
                        {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                })
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
                import json as _json
                data = _json.loads(raw)
                questoes_extraidas = data if isinstance(data, list) else data.get("questoes", data.get("gabarito", []))
            except Exception:
                questoes_extraidas = []
    else:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado para extração de gabarito")

    for item in questoes_extraidas:
        num = int(item.get("numero_questao", 0))
        resp = item.get("resposta_correta", "").strip().upper()
        if not num or not resp:
            continue
        q = next((q for q in questoes_db if q.numero_questao == num), None)
        if q:
            q.resposta_correta = resp

    db.commit()

    return GabaritoExtraidoResponse(
        questoes=[QuestaoGabarito(numero_questao=q.numero_questao, resposta_aluno=q.resposta_aluno, resposta_correta=q.resposta_correta) for q in questoes_db],
        metodo="ia" if questoes_extraidas else "nenhum",
    )
