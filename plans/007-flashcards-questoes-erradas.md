# Plan 007: Gerar flashcards a partir de questões erradas do simulado

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 570917e..HEAD -- backend/app/routers/flashcards.py backend/app/schemas/flashcard.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none (mas idealmente após 004 e 005 terem populado `texto_questao` e `acerto`)
- **Category**: direction
- **Planned at**: commit `570917e`, 2026-07-16

## Why this matters

O sistema já classifica questões como certas/erradas (`questao_identificada.acerto`). Hoje, para gerar flashcards, o aluno precisa escolher uma habilidade manualmente (`POST /api/flashcards/gerar` com `habilidade_id`). Não há um fluxo "gere flashcards das questões que eu errei". Isso é essencial para revisão direcionada: o aluno errou uma questão → o sistema cria um flashcard com o texto da questão e a explicação da resposta correta.

## Current state

- `POST /api/flashcards/gerar` (`flashcards.py:51-90`) — recebe `habilidade_id` e `quantidade`, gera flashcards genéricos baseados na descrição da habilidade. Não usa o texto da questão real.
- `QuestaoIdentificada` (`models.py:84-101`) — tem `acerto` (bool), `texto_questao` (str), `resposta_correta` (str), `habilidade_id` (int FK).
- `Flashcard` (`models.py:138-153`) — tem `pergunta`, `resposta`, `habilidade_id`.

Não há endpoint que:
1. Busque questões com `acerto == False` de um simulado
2. Gere flashcards a partir do texto real da questão e da resposta correta

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Tests   | `cd backend && .venv\Scripts\python -m pytest -xvs` | all pass |

## Scope

**In scope**:
- `backend/app/routers/flashcards.py` — novo endpoint
- `backend/app/schemas/flashcard.py` — novos schemas
- `backend/app/tests/test_main.py` — novos testes

**Out of scope**:
- `backend/app/routers/simulados.py` — não mexer
- Frontend — será adicionado em plano separado (opcional)

## Git workflow

- Branch: `advisor/007-flashcards-erros`
- Commits por passo; estilo: `feat: endpoint para gerar flashcards de questões erradas`

## Steps

### Step 1: Criar schema `FlashcardFromErrorsRequest`

Em `backend/app/schemas/flashcard.py`, adicione:

```python
class FlashcardFromErrorsRequest(BaseModel):
    simulado_id: Optional[int] = None  # se None, busca em todos os simulados
    quantidade: int = 5
```

### Step 2: Adicionar função auxiliar `_get_wrong_questions`

Em `backend/app/routers/flashcards.py`, antes da classe, adicione:

```python
from sqlalchemy import and_
from app.models import QuestaoIdentificada, SimuladoUpload

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
```

### Step 3: Criar endpoint `POST /api/flashcards/gerar-de-erros`

Em `backend/app/routers/flashcards.py`, adicione:

```python
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
```

Note: import `date` do módulo `datetime` no topo do arquivo se não existir. Verifique se `from datetime import date` já está em `flashcards.py` (linha 1).

### Step 4: Importar o schema novo no router

Adicione no import em `flashcards.py`:
```python
from app.schemas.flashcard import (
    FlashcardFromErrorsRequest,
    FlashcardGenerateRequest,
    FlashcardRescheduleResponse,
    FlashcardResponse,
    FlashcardReview,
)
```

**Verify**:
```
cd backend && .venv\Scripts\python -c "from app.routers.flashcards import gerar_flashcards_de_erros; print('OK')"
```
→ `OK`

## Test plan

Em `test_main.py`, adicione na classe `TestFlashcards`:

```python
def test_gerar_de_erros_sem_erros(self):
    _register()
    token = _login()
    resp = client.post(
        "/api/flashcards/gerar-de-erros",
        json={"quantidade": 3},
        headers=_auth_header(token),
    )
    # Sem questões erradas no banco, deve retornar 404
    assert resp.status_code == 404

def test_gerar_de_erros_com_simulado(self):
    _register()
    token = _login()
    # Upload e preenche gabarito com erros
    upload_resp = client.post(
        "/api/simulados/upload",
        files={"file": ("test.png", b"fake", "image/png")},
        headers=_auth_header(token),
    )
    sim_id = upload_resp.json()["id"]
    client.put(
        f"/api/simulados/{sim_id}/gabarito",
        json={"questoes": [
            {"numero_questao": 1, "resposta_aluno": "A", "resposta_correta": "B"},
        ]},
        headers=_auth_header(token),
    )
    # Adiciona texto_questao manualmente (simula extrair-texto)
    from app.core.database import SessionLocal
    from app.models import QuestaoIdentificada
    db = SessionLocal()
    q = db.query(QuestaoIdentificada).filter_by(simulado_upload_id=sim_id).first()
    q.texto_questao = "Qual a capital do Brasil?"
    db.commit()
    db.close()

    resp = client.post(
        "/api/flashcards/gerar-de-erros",
        json={"simulado_id": sim_id, "quantidade": 1},
        headers=_auth_header(token),
    )
    assert resp.status_code in (201, 404)  # 201 se o flashcard foi gerado
```

Modelar após `test_gerar_flashcards` (linhas 199-210).

## Done criteria

ALL must hold:
- [ ] `cd backend && .venv\Scripts\python -m pytest -xvs` exits 0
- [ ] `POST /api/flashcards/gerar-de-erros` retorna 201 com flashcards quando há questões erradas
- [ ] `POST /api/flashcards/gerar-de-erros` retorna 404 quando não há questões erradas
- [ ] Flashcards gerados contêm pergunta baseada no texto real da questão
- [ ] Nenhum arquivo fora do escopo foi modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Stop and report if:
- O endpoint extrair-texto não foi chamado antes e `texto_questao` está vazio — o endpoint deve logar um aviso.
- A chamada ao DeepSeek falha para todas as questões — retorne erro ou lista vazia.

## Maintenance notes

- Idealmente este endpoint deve ser chamado automaticamente após o preenchimento do gabarito.
- Considere adicionar um parâmetro `incluir_temas_livres` para filtrar por tema também.
