# Plan 004: Roteamento automático de upload por tipo de arquivo (imagem → Qwen OCR, PDF → MarkItDown)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 570917e..HEAD -- backend/app/routers/simulados.py backend/app/services/ai_provider/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `570917e`, 2026-07-16

## Why this matters

O endpoint `POST /api/simulados/upload` salva qualquer arquivo sem distinguir seu tipo. Quando o usuário faz upload de um PDF, o sistema não sabe disso até que ele clique em "Extrair Texto". A rota de upload deve identificar o tipo MIME / extensão e disparar o pipeline correto: imagens (png/jpg/jpeg) vão para OCR via Qwen (ou DeepSeek fallback), PDFs vão para MarkItDown. Isso elimina a dupla chamada e prepara o terreno para extração automática de gabarito.

## Current state

- `backend/app/routers/simulados.py:73-95` — endpoint `/upload` aceita `UploadFile` genérico, salva no disco, cria registro `SimuladoUpload` com `tipo="caderno_prova"` e para por aí. Não lê o tipo real do arquivo.
- `backend/app/routers/simulados.py:49-57` — funções `_is_pdf()` e `_convert_pdf_to_markdown()` já existem mas nunca são chamadas no upload.
- `backend/app/routers/simulados.py:42-46` — `_ocr()` tenta Qwen primeiro, depois cai para DeepSeek.
- Convenção do repositório: Pydantic `from_attributes=True` nos schemas, SQLAlchemy async sessions via `get_db()`, handlers em routers com `aluno: Aluno = Depends(get_aluno_atual)`.

## Commands you will need

| Purpose   | Command                                                | Expected on success |
|-----------|--------------------------------------------------------|---------------------|
| Install   | `cd backend && .venv\Scripts\pip install markitdown[pdf]` | exit 0              |
| Tests     | `cd backend && .venv\Scripts\python -m pytest -xvs`   | all pass            |
| Run       | `cd backend && .venv\Scripts\uvicorn app.main:app --reload` | server starts       |

## Scope

**In scope** (the only files you should modify):
- `backend/app/routers/simulados.py`
- `backend/app/tests/test_main.py` (adicionar testes)

**Out of scope** (do NOT touch, even though they look related):
- `backend/app/routers/redacao.py` — mesmo padrão de _ai()/_ocr() mas será tratado em plano separado
- `backend/app/services/ai_provider/` — não modificar os providers

## Git workflow

- Branch: `advisor/004-roteamento-upload`
- Commit por passo; mensagens no estilo: `feat: extrair tipo MIME no upload e rotear para pipeline correto`
- Do NOT push ou abrir PR a menos que instruído.

## Steps

### Step 1: Adicionar função `_is_image()` e melhorar `_is_pdf()`

Em `backend/app/routers/simulados.py`, abaixo da função `_is_pdf()` existente (linha 49), adicione:

```python
def _is_image(path: str) -> bool:
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"))
```

A função `_is_pdf()` já existe (linha 49-50) — mantenha.

**Verify**: O código importa sem erros:
```
cd backend && .venv\Scripts\python -c "from app.routers.simulados import _is_image, _is_pdf; print('OK')"
```
→ `OK`

### Step 2: Refatorar endpoint `/upload` para detectar tipo e rotear

Substitua o corpo de `upload_simulado` (linhas 73-95) para:

1. Detectar extensão do `file.filename`
2. Se `_is_pdf(caminho)`: salvar o PDF, após salvar chamar `_convert_pdf_to_markdown(caminho)` e já armazenar o texto extraído (precisa de um campo novo ou reutilizar a lógica existente). Para não quebrar o schema atual, apenas armazene o caminho — a conversão é sob demanda.
3. Se `_is_image(caminho)`: salvar a imagem normalmente.
4. Se nenhum dos dois: retornar HTTP 400.

O endpoint deve armazenar uma nova coluna `tipo_real` (vamos usar o campo `tipo` existente para isso — mapear `ext` para `"pdf"`, `"imagem"`, `"desconhecido"`):

```python
ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
if ext in ("pdf",):
    tipo_real = "pdf"
elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
    tipo_real = "imagem"
else:
    raise HTTPException(status_code=400, detail=f"Tipo de arquivo não suportado: {ext}")
```

Modifique a criação do `SimuladoUpload` para usar `tipo=tipo_real`.

**Verify**:
```
cd backend && .venv\Scripts\python -m pytest -xvs -k "test_upload"
```
→ Testes passam (o teste existente envia PNG, deve continuar funcionando).

### Step 3: Modificar `detectar_estrutura` para usar MarkItDown em PDFs reais

No endpoint `detectar_estrutura` (linhas 98-150), substitua o trecho de hardcoded:
```python
elif _is_pdf(simulado.arquivo_path) and not qwen.api_key:
    estrutura = {"total_questoes": 90, "alternativas_por_questao": 5, "numeracao_inicial": 1}
```
para usar MarkItDown de verdade:
```python
elif _is_pdf(simulado.arquivo_path):
    md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
    prompt = (
        "Analise o texto abaixo extraído de um PDF de prova ENEM e determine:\n"
        "- Quantidade total de questões\n"
        "- Número de alternativas por questão (4 ou 5)\n"
        "- Numeração inicial\n"
        "Retorne JSON: {\"total_questoes\": N, \"alternativas_por_questao\": N, \"numeracao_inicial\": N}\n\n"
        f"Texto:\n{md_text[:8000]}"
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
            "max_tokens": 1024,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    import json as _json
    estrutura = _json.loads(raw)
```

Se não houver `ai().api_key`, mantenha o fallback hardcoded.

**Verify**: 
```
cd backend && .venv\Scripts\python -m pytest -xvs -k "test_simulado"
```
→ Testes passam.

## Test plan

- Adicionar em `backend/app/tests/test_main.py` classe `TestUploadTipos`:
  - `test_upload_pdf`: envia `.pdf` fake, verifica `tipo == "pdf"`, status 201
  - `test_upload_png`: envia `.png`, verifica `tipo == "imagem"`, status 201
  - `test_upload_tipo_invalido`: envia `.txt`, verifica status 400
- Modelar após `test_upload_and_get` existente (linhas 117-130).

**Verification**: `cd backend && .venv\Scripts\python -m pytest -xvs` → todos os testes passam, incluindo os 3 novos.

## Done criteria

ALL must hold:
- [ ] `cd backend && .venv\Scripts\python -m pytest -xvs` exits 0
- [ ] Upload de PNG resulta em `tipo == "imagem"` no banco
- [ ] Upload de PDF resulta em `tipo == "pdf"` no banco
- [ ] Upload de `.txt` retorna 400
- [ ] `detectar_estrutura` em PDF (sem Qwen key) usa DeepSeek sobre MarkItDown, não hardcoded 90
- [ ] Nenhum arquivo fora do escopo foi modificado (`git status`)
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Stop and report back if:
- O código em `simulados.py` difere significativamente dos excerpts (drift pós-570917e).
- `markitdown` não pode ser instalado no `.venv`.
- Um teste novo falha após 2 tentativas de correção razoável.

## Maintenance notes

- Quando a extração automática de gabarito for implementada (plano 005), o upload de PDF deve disparar a extração do gabarito da última página automaticamente.
- O upload de imagens pode ser estendido para também extrair gabarito via visão computacional.
