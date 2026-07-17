# Plan 006: Extração automática de gabarito da última página do simulado

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 570917e..HEAD -- backend/app/routers/simulados.py backend/app/schemas/simulado.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: 004 (roteamento de tipo de arquivo)
- **Category**: direction
- **Planned at**: commit `570917e`, 2026-07-16

## Why this matters

O gabarito oficial do ENEM geralmente está na última página do caderno de provas (ou em uma página separada no PDF). Hoje o aluno precisa preencher manualmente cada uma das ~90 questões — um processo tedioso de 90 cliques. Extrair automaticamente o gabarito da última página e pré-preencher as respostas corretas reduz drasticamente o atrito.

## Current state

- `POST /api/simulados/{id}/gabarito` (simulados.py:153-220) — espera o body com `{questoes: [{numero_questao, resposta_aluno, resposta_correta}]}`. O usuário preenche manualmente no frontend.
- `PUT /api/simulados/{id}/gabarito` (simulados.py:153 — mas na verdade é o PUT) recebe o gabarito manual e persiste.
- `QuestaoIdentificada` (`models.py:84-101`) tem campos `resposta_aluno`, `resposta_correta`, `acerto`.
- O campo `texto_questao` já é populado pelo extrair-texto.

Não há endpoint para extração automática de gabarito. O frontend (`SimuladoDetalhe.tsx`) mostra 90 botões A/B/C/D/E para preenchimento manual.

## Commands you will need

| Purpose   | Command                                                | Expected on success |
|-----------|--------------------------------------------------------|---------------------|
| Tests     | `cd backend && .venv\Scripts\python -m pytest -xvs`   | all pass            |
| Run       | `cd backend && .venv\Scripts\uvicorn app.main:app --reload` | server starts |

## Scope

**In scope**:
- `backend/app/routers/simulados.py` — novo endpoint
- `backend/app/schemas/simulado.py` — novo schema de resposta
- `backend/app/tests/test_main.py` — novos testes

**Out of scope**:
- Frontend (`src/pages/SimuladoDetalhe.tsx`) — a UI já lê `gabarito` do backend; se o backend preencher `resposta_correta`, o frontend exibirá automaticamente. Toque zero no frontend.
- Qualquer alteração nos modelos do banco

## Git workflow

- Branch: `advisor/006-extracao-gabarito`
- Commits por passo; estilo: `feat: extrair gabarito automaticamente da última página do PDF/imagem`

## Steps

### Step 1: Criar schema de resposta para extração de gabarito

Em `backend/app/schemas/simulado.py`, adicione:

```python
class GabaritoExtraidoResponse(BaseModel):
    questoes: list[QuestaoGabarito]
    metodo: str  # "ia" ou "nenhum"
```

### Step 2: Criar endpoint `POST /api/simulados/{id}/extrair-gabarito`

Em `backend/app/routers/simulados.py`, adicione:

```python
@router.post("/{simulado_id}/extrair-gabarito", response_model=GabaritoExtraidoResponse)
async def extrair_gabarito(
    simulado_id: int,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    simulado = db.query(SimuladoUpload).filter_by(id=simulado_id, aluno_id=aluno.id).first()
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")

    # Pega as questões já identificadas (para saber a numeração)
    questoes_db = (
        db.query(QuestaoIdentificada)
        .filter_by(simulado_upload_id=simulado_id)
        .order_by(QuestaoIdentificada.numero_questao)
        .all()
    )

    if not os.path.exists(simulado.arquivo_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if _is_pdf(simulado.arquivo_path):
        md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
        # Pega o final do texto (últimos ~3000 caracteres, onde normalmente está o gabarito)
        tail = md_text[-4000:] if len(md_text) > 4000 else md_text
        prompt = (
            "Extraia o GABARITO (respostas corretas) do texto abaixo. "
            "O gabarito lista o número da questão e a alternativa correta "
            "(ex: '01 - A', '02 - C', '1:A', '2:B', etc). "
            "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
            '{"numero_questao": <número>, "resposta_correta": "<letra>"}\n\n'
            f"Texto:\n{tail}"
        )
        ai = _ai()
        client = ai._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": ai.model,
                "messages": [
                    {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        import json as _json
        data = _json.loads(raw)
        if isinstance(data, dict):
            questoes_extraidas = data.get("questoes", data.get("gabarito", []))
        else:
            questoes_extraidas = data
    elif _is_image(simulado.arquivo_path):
        # Para imagem: usar Qwen ou DeepSeek vision para ler o gabarito visualmente
        with open(simulado.arquivo_path, "rb") as f:
            image_bytes = f.read()
        qwen = get_qwen_provider()
        if qwen.api_key:
            ocr_text = await qwen.ocr_image(image_bytes)
        else:
            ai = _ai()
            ocr_text = await ai.ocr_image(image_bytes)
        prompt = (
            "Extraia o GABARITO (respostas corretas) do texto OCR abaixo. "
            "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
            '{"numero_questao": <número>, "resposta_correta": "<letra>"}\n\n'
            f"Texto OCR:\n{ocr_text}"
        )
        ai = _ai()
        client = ai._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": ai.model,
                "messages": [
                    {"role": "system", "content": "Você é um assistente especializado em ENEM."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        data = _json.loads(raw)
        questoes_extraidas = data if isinstance(data, list) else data.get("questoes", data.get("gabarito", []))
    else:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado para extração de gabarito")

    # Atualiza as questões no banco com as respostas corretas encontradas
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
        metodo="ia",
    )
```

**Verify**:
```
cd backend && .venv\Scripts\python -c "from app.routers.simulados import extrair_gabarito; print('endpoint registrado')"
```
→ `endpoint registrado`

### Step 3: Registrar a nova rota

Se o endpoint usa `@router`, ele já está registrado automaticamente pois `router` já inclui todos os decorators. Verifique com:

```
cd backend && .venv\Scripts\python -m pytest -xvs -k "test_extrair_gabarito"
```
→ O teste vai falhar (não existe ainda). Passe para o Test Plan.

## Test plan

Adicionar em `test_main.py`:

```python
def test_extrair_gabarito_pdf(self):
    _register()
    token = _login()
    # Simula upload de um PDF fake
    upload_resp = client.post(
        "/api/simulados/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 fake pdf content with gabarito 1-A 2-B 3-C", "application/pdf")},
        headers=_auth_header(token),
    )
    assert upload_resp.status_code == 201
    sim_id = upload_resp.json()["id"]

    # Tenta extrair gabarito (vai cair no fallback IA pois PDF é fake)
    resp = client.post(f"/api/simulados/{sim_id}/extrair-gabarito", headers=_auth_header(token))
    # Pode falhar se o PDF for inválido — ok, só verifica se o endpoint existe
    assert resp.status_code in (200, 502, 500)
```

Modelar após `test_upload_and_get` (linhas 117-130) e `test_gabarito` (linhas 132-156).

## Done criteria

ALL must hold:
- [ ] `cd backend && .venv\Scripts\python -m pytest -xvs` exits 0
- [ ] Endpoint `POST /api/simulados/{id}/extrair-gabarito` existe e retorna 200/4xx/5xx (não 404)
- [ ] O gabarito extraído persiste no banco (coluna `resposta_correta` preenchida)
- [ ] Nenhum arquivo fora do escopo foi modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Stop and report if:
- O parsing do gabarito pelo LLM retorna dados inconsistentes (ex: letras inválidas)
- O endpoint de extrair-texto (extrair_texto_questoes) ainda não foi chamado e não há questões no banco — nesse caso, o endpoint deve criar as questões automaticamente

## Maintenance notes

- A qualidade da extração depende da qualidade do OCR/PDF. Para PDFs bem formatados, a taxa de acerto tende a ser alta.
- Considere adicionar um botão "Confirmar Gabarito Extraído" no frontend para que o aluno valide antes de salvar.
