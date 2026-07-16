# Plano 001: Backend — extrair texto e classificar questões via IA

> **Instruções ao executor**: Siga este plano passo a passo. Execute cada
> comando de verificação e confirme o resultado esperado antes de avançar.
> Se algo nas "STOP conditions" ocorrer, PARE e reporte — não improvise.
> Ao finalizar, atualize a linha de status em `plans/README.md`.
>
> **Drift check (execute primeiro)**: `git diff --stat 3446e5f..HEAD -- backend/app/models.py backend/app/schemas/simulado.py backend/app/routers/simulados.py backend/app/services/ai_provider/`
> Se algum arquivo in-scope mudou desde o SHA do plano, compare os
> trechos de "Current state" com o código atual antes de prosseguir;
> em caso de divergência, trate como STOP condition.

## Status

- **Prioridade**: P1
- **Esforço**: M
- **Risco**: LOW
- **Depende de**: nenhum
- **Categoria**: direction
- **Planned at**: commit `3446e5f`, 2026-07-16

## Por que isso importa

O Medvest já tem o provider de IA com o método `classify_question`
implementado, mas ele **nunca é chamado**. As questões ficam sem
classificação (`habilidade_id` = NULL), o que impede o motor de
priorização de funcionar corretamente e o dashboard de mostrar
dados por habilidade. Este plano conecta a IA ao fluxo real:
extrai o texto de cada questão do caderno de provas por OCR,
classifica cada uma na matriz ENEM, e persiste o resultado.

## Estado atual

- `backend/app/models.py:84-101` — `QuestaoIdentificada` tem os campos
  `habilidade_id`, `tema_livre`, `dificuldade_estimada` que ficam NULL;
  **não tem** campo para armazenar o texto extraído da questão.

- `backend/app/models.py:7-43` — `Area` → `Competencia` → `Habilidade`
  formam a hierarquia ENEM (4 áreas, 120 habilidades H1-H30).

- `backend/app/routers/simulados.py:114-179` — `preencher_gabarito`
  só salva `resposta_aluno` + `resposta_correta`, não chama IA.

- `backend/app/services/ai_provider/deepseek_provider.py:82-111` —
  `classify_question()` já existe: recebe `question_text` + `image_bytes`,
  chama DeepSeek, retorna JSON com `area`, `competencia`, `habilidade`,
  `tema_livre`, `dificuldade`.

- `backend/app/services/ai_provider/deepseek_provider.py:54-80` —
  `ocr_image()` já existe: recebe `image_bytes`, transcreve texto via DeepSeek.

**Convenções do repositório — siga estritamente**:
- SQLAlchemy 2.0 com `Mapped` / `mapped_column`
- Pydantic v2 com `model_config = ConfigDict(from_attributes=True)`
- FastAPI routers com `Depends(get_aluno_atual)` para auth
- `_ai()` no router faz fallback automático se não houver API key
- Mensagens de commit: `sprint-X: descrição` (ex: `git log --oneline -5`)

## Comandos que você vai precisar

| Propósito | Comando | Esperado |
|-----------|---------|----------|
| Instalar deps | `pip install -r backend\requirements.txt` | exit 0 |
| Testes | `cd backend; pytest . -v` | all pass |
| Servidor | `cd backend; uvicorn app.main:app --reload` | sobe em :8000 |

## Escopo

**In scope** (únicos arquivos a modificar):
- `backend/app/models.py` — adicionar campo `texto_questao`
- `backend/app/schemas/simulado.py` — adicionar campo nos schemas de response/request
- `backend/app/routers/simulados.py` — adicionar endpoints `POST /{id}/extrair-texto` e `POST /{id}/classificar`
- `backend/app/services/ai_provider/deepseek_provider.py` — (se necessário) ajustar prompt do `classify_question`
- `backend/app/services/ai_provider/fallback_ocr.py` — (se necessário) atualizar fallback

**Out of scope** (NÃO tocar):
- Frontend (é o plano 002)
- Modelos `Area`, `Competencia`, `Habilidade`, `Aluno`, `DominioHabilidade` etc.
- Autenticação, dashboard, flashcards

## Git workflow

- Branch: `sprint-4-classificacao-ia`
- Commits atômicos por passo
- `git commit -m "sprint-4: <descrição>"`
- Não fazer push a menos que instruído

## Passos

### Passo 1: Adicionar campo `texto_questao` no modelo

Em `backend/app/models.py`, dentro de `QuestaoIdentificada`, adicionar:

```python
texto_questao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Verificar**: `python -c "from app.models import QuestaoIdentificada; print([c.name for c in QuestaoIdentificada.__table__.columns])"` → deve incluir `texto_questao`

### Passo 2: Atualizar schemas Pydantic

Em `backend/app/schemas/simulado.py`:

2.1. Em `QuestaoIdentificadaResponse`, adicionar:
```python
texto_questao: Optional[str] = None
```

2.2. Criar `class QuestaoClassificacaoInput(BaseModel):`:
```python
class QuestaoClassificacaoInput(BaseModel):
    numero_questao: int
    question_text: str  # texto extraído por OCR para esta questão
```

2.3. Criar `class ClassificarRequest(BaseModel):`:
```python
class ClassificarRequest(BaseModel):
    questoes: list[QuestaoClassificacaoInput]
```

2.4. Criar `class ClassificacaoOutput(BaseModel):`:
```python
class ClassificacaoOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_questao: int
    habilidade_codigo: Optional[str] = None
    tema_livre: Optional[str] = None
    dificuldade_estimada: Optional[float] = None
    texto_questao: Optional[str] = None
    classificacao_confirmada_manualmente: bool = False
```

2.5. Criar `class ClassificarResponse(BaseModel):`:
```python
class ClassificarResponse(BaseModel):
    questoes: list[ClassificacaoOutput]
```

**Verificar**: `cd backend; python -c "from app.schemas.simulado import ClassificarResponse; print('OK')"` → OK

### Passo 3: Extrair texto — novo endpoint `POST /{id}/extrair-texto`

Em `backend/app/routers/simulados.py`, adicionar endpoints. O fluxo:

3.1. Endpoint que OCR a imagem completa do caderno, depois usa a IA para
segmentar o texto por questão.

```python
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

    ai = _ai()

    # OCR completo do caderno
    texto_completo = await ai.ocr_image(image_bytes)

    # IA segmenta o texto por questão
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"O texto abaixo é a transcrição de um caderno de provas ENEM. "
            f"Identifique cada questão e retorne um JSON array, onde cada elemento tem:\n"
            f"{{\"numero\": N, \"texto\": \"...\"}}\n\n"
            f"Use APENAS o texto fornecido. Se não conseguir identificar o texto de uma questão, "
            f"retorne texto vazio para ela.\n\n"
            f"Texto completo:\n{texto_completo}"
        )},
    ]
    # NOTE: usamos o método _call diretamente ou criamos um helper.
    # Como _call é privado, vamos reutilizar o client do provider.
    # Na prática, podemos chamar o _call do provider:
    import json
    from app.services.ai_provider.deepseek_provider import DeepSeekProvider
    if isinstance(ai, DeepSeekProvider):
        result = await ai._call(messages, max_tokens=8192)
        questoes_texto = json.loads(result)
    else:
        # Fallback:粗略分割 por linhas
        lines = texto_completo.strip().split("\n")
        questoes_texto = []
        for i, line in enumerate(lines):
            questoes_texto.append({"numero": i + 1, "texto": line[:200]})

    # Atualiza as questões existentes ou cria novas
    resp = []
    for item in questoes_texto:
        num = item.get("numero", item.get("numero_questao", 0))
        texto = item.get("texto", "")
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
        questoes=[ClassificacaoOutput(
            id=q.id,
            numero_questao=q.numero_questao,
            texto_questao=q.texto_questao,
            classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
        ) for q in resp]
    )
```

**IMPORTANTE**: O `SYSTEM_PROMPT` precisa ser importado. Adicione no topo do
arquivo:
```python
from app.services.ai_provider.deepseek_provider import SYSTEM_PROMPT
```

E o `_call` é um método privado. Para o fallback, trate como no código acima.
Para o provider real, precisamos acessar `_call`. Como é um método existente,
vamos usá-lo diretamente — é seguro pois está dentro do nosso módulo.

**Verificar**: Suba o servidor e chame `curl -X POST http://localhost:8000/api/simulados/1/extrair-texto` com token JWT → retorna 200 com lista de questões.

### Passo 4: Endpoint `POST /{id}/classificar`

Este endpoint chama `classify_question` para cada questão que tem texto,
e atualiza `habilidade_id`, `tema_livre`, `dificuldade_estimada`.

```python
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

    resp = []
    for q in questoes:
        texto = q.texto_questao or ""
        if not texto.strip():
            resp.append(ClassificacaoOutput(
                id=q.id,
                numero_questao=q.numero_questao,
                texto_questao=q.texto_questao,
            ))
            continue

        try:
            result = await ai.classify_question(texto, image_bytes)
        except Exception as e:
            continue  # pula questões que falharem

        area_nome = result.get("area", "")
        habilidade_codigo = result.get("habilidade", "")
        tema_livre = result.get("tema_livre", "")
        dificuldade_raw = result.get("dificuldade", "media")

        # Mapeia dificuldade para float
        dificuldade_map = {"facil": 1.0, "media": 2.0, "dificil": 3.0}
        q.dificuldade_estimada = dificuldade_map.get(dificuldade_raw, 2.0)
        q.tema_livre = tema_livre

        # Busca habilidade pelo código
        if habilidade_codigo:
            habilidade = (
                db.query(Habilidade)
                .filter_by(codigo=habilidade_codigo)
                .first()
            )
            if habilidade:
                q.habilidade_id = habilidade.id

        resp.append(q)

    db.commit()

    # Recalcular prioridades após classificar
    from app.services.prioritization import recalcular_prioridades
    recalcular_prioridades(db, aluno.id)

    return ClassificarResponse(
        questoes=[ClassificacaoOutput(
            id=q.id,
            numero_questao=q.numero_questao,
            habilidade_codigo=q.habilidade.codigo if q.habilidade else None,
            tema_livre=q.tema_livre,
            dificuldade_estimada=q.dificuldade_estimada,
            texto_questao=q.texto_questao,
            classificacao_confirmada_manualmente=q.classificacao_confirmada_manualmente,
        ) for q in questoes]
    )
```

Adicione o import de `Habilidade` no topo do arquivo.

**Verificar**: `curl -X POST http://localhost:8000/api/simulados/1/classificar` → retorna 200 com cada questão classificada.

### Passo 5: Atualizar `obter_simulado` para incluir `texto_questao`

Em `backend/app/routers/simulados.py`, no endpoint `obter_simulado`, o response
já inclui `texto_questao` via `QuestaoIdentificadaResponse`. Verifique se o
campo está sendo populado — o schema já tem `texto_questao: Optional[str]` do
Passo 2, e o model agora tem o campo.

**Verificar**: `GET /api/simulados/{id}` → cada questão inclui `texto_questao`.

### Passo 6: Atualizar `preencher_gabarito` para não sobrescrever classificação

Em `backend/app/routers/simulados.py:129-152`, no loop de `preencher_gabarito`,
o `QuestaoIdentificada` é criado sem os campos de classificação. Isso está
correto — a classificação vem depois. Mas ao criar nova instância (linha 144),
adicione `texto_questao=None` explicitamente para clareza (já é default).

**Verificar**: envie um PUT /gabarito → questões criadas sem classificação.

## Plano de teste

1. **Teste unitário do provider**: criar `backend/app/services/ai_provider/test_provider.py`
   que testa `classify_question` com texto mock e verifica se retorna o formato esperado.
   Usar mock do httpx para não chamar API real.
   Modelo após `backend/app/tests/test_main.py`.

2. **Teste do endpoint classificar**: em `backend/app/tests/`, adicionar teste
   que cria um simulado + questão, chama `POST /classificar` com mock do provider,
   e verifica que `habilidade_id` foi populado.

**Verificar**: `cd backend; pytest . -v` → todos os testes existentes + novos passam.

## Done criteria

- [ ] `QuestaoIdentificada` tem coluna `texto_questao`
- [ ] `POST /{id}/extrair-texto` retorna 200 com texto extraído por questão
- [ ] `POST /{id}/classificar` retorna 200 com classificação por questão
- [ ] Questões classificadas têm `habilidade_id`, `tema_livre`, `dificuldade_estimada` populados
- [ ] `cd backend; pytest . -v` passa
- [ ] Nenhum arquivo fora do escopo foi modificado (`git status`)
- [ ] `plans/README.md` atualizado

## STOP conditions

Pare e reporte se:

- O modelo `QuestaoIdentificada` não corresponder aos trechos do "Estado atual"
  (o código-base pode ter mudado desde que o plano foi escrito).
- A verificação de um passo falhar duas vezes após uma tentativa razoável de corrigir.
- A implementação exigir tocar em arquivo fora do escopo.
- A API DeepSeek retornar consistentemente formato diferente do esperado
  (ex: campos `area`/`habilidade` ausentes).

## Notas de manutenção

- O endpoint `extrair-texto` faz duas chamadas de IA (OCR + segmentação).
  Se o custo for alto, futuramente podemos fazer em uma chamada só pedindo
  que a IA já retorne o texto segmentado por questão diretamente.
- A classificação individual por questão (N chamadas) pode ser substituída
  por uma chamada batch se a latência for um problema.
- A função `recalcular_prioridades` é chamada após classificar para atualizar
  o motor de priorização. Se houver muitas questões, isso pode ser pesado.
