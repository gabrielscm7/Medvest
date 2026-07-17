# Plan 005: Otimizar extrair-texto para PDF (DeepSeek lê MarkDown direto, sem re-chamada de LLM visual)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 570917e..HEAD -- backend/app/routers/simulados.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 004 (que cria o pipeline de detecção de tipo de arquivo)
- **Category**: performance
- **Planned at**: commit `570917e`, 2026-07-16

## Why this matters

Atualmente, quando o arquivo é PDF e o usuário clica "Extrair Texto" (`simulados.py:343-366`), o sistema:
1. Converte PDF → MarkDown via MarkItDown (certo)
2. Envia o MarkDown inteiro para DeepSeek com o prompt "Analise este texto... retorne JSON array" (redundante!)

MarkItDown já extraiu o texto estruturado. O DeepSeek não precisa re-analisar o texto — ele só precisa ler o MarkDown diretamente e identificar as questões. Na prática, o MarkDown do PDF já contém as questões numeradas. Podemos pular a chamada LLM quando o texto extraído já é bem estruturado.

## Current state

- `backend/app/routers/simulados.py:343-366` — dentro de `extrair_texto_questoes`, para PDF:
  ```python
  if _is_pdf(simulado.arquivo_path):
      md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
      prompt = (
          "Analise este texto de prova ENEM extraído de um PDF. "
          "Identifique CADA questão individualmente e extraia o texto completo de cada uma. "
          "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
          '{"numero": <número>, "texto": "<texto completo>"}\n\n'
          "Extraia TODAS as questões. Responda apenas o JSON, sem explicações.\n\n"
          f"Texto:\n{md_text}"
      )
      client = ai._get_client()
      response = await client.post(...)
  ```
- O resultado do DeepSeek é parseado como JSON para extrair as questões (linhas 398-404).

## Commands you will need

| Purpose   | Command                                                | Expected on success |
|-----------|--------------------------------------------------------|---------------------|
| Tests     | `cd backend && .venv\Scripts\python -m pytest -xvs`   | all pass            |
| Lint      | `cd backend && .venv\Scripts\python -m flake8` (se houver) | exit 0        |

## Scope

**In scope**:
- `backend/app/routers/simulados.py`

**Out of scope**:
- `backend/app/routers/redacao.py` — mesmo padrão, tratado separadamente
- `backend/app/services/ai_provider/` — não modificar

## Git workflow

- Branch: `advisor/005-otimizar-extrair-texto-pdf`
- Commits por passo; estilo: `perf: pular chamada LLM quando PDF já foi convertido para MD`

## Steps

### Step 1: Adicionar extração direta de questões do MarkDown

A abordagem: em vez de enviar o MarkDown para DeepSeek re-analisar, use parsing simples de regex para extrair as questões numeradas do texto MarkDown. O formato típico de um PDF convertido é:

```
## Questão 1
Texto da questão...

## Questão 2
Texto da questão...
```

ou

```
1. Texto da questão...
2. Texto da questão...
```

Adicione uma função `_parse_questions_from_md(md_text: str) -> list[dict]`:

```python
import re

def _parse_questions_from_md(md_text: str) -> list[dict]:
    questions = []
    pattern = r'(?:^|\n)(?:\#+\s*)?(?:Questão\s*)?(\d+)[\.\):]\s*\n?(.*?)(?=\n(?:Questão\s*)?\d+[\.\):]\s|\Z)'
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
```

**Verify**:
```
cd backend && .venv\Scripts\python -c "
from app.routers.simulados import _parse_questions_from_md
md = '## Questão 1\nTexto da um.\n## Questão 2\nTexto da dois.'
q = _parse_questions_from_md(md)
print(len(q), q[0]['numero'], q[0]['texto'][:10])
" 
```
→ `2 1 Texto da u`

### Step 2: Substituir a chamada DeepSeek no extrair-texto para PDF

No endpoint `extrair_texto_questoes`, substitua o bloco `if _is_pdf(...):` (linhas 343-366) por:

```python
if _is_pdf(simulado.arquivo_path):
    md_text = _convert_pdf_to_markdown(simulado.arquivo_path)
    questoes_texto = _parse_questions_from_md(md_text)
    if not questoes_texto:
        # fallback: usa DeepSeek como antes se o parsing simples falhar
        prompt = (
            "Analise este texto de prova ENEM extraído de um PDF. "
            "Identifique CADA questão individualmente e extraia o texto completo de cada uma. "
            "Retorne UM JSON ARRAY, onde cada elemento tem:\n"
            '{"numero": <número>, "texto": "<texto completo>"}\n\n'
            "Extraia TODAS as questões. Responda apenas o JSON, sem explicações.\n\n"
            f"Texto:\n{md_text[:16000]}"
        )
        client = ai._get_client()
        response = await client.post(...)
        # ... (mesmo código existente de parse da resposta)
```

Ou seja: tenta parse local primeiro (zero custo). Só chama LLM se o parsing falhar.

**Verify**:
```
cd backend && .venv\Scripts\python -m pytest -xvs
```
→ Todos os testes passam.

## Test plan

Adicionar em `test_main.py`:

```python
def test_parse_questions_from_md():
    from app.routers.simulados import _parse_questions_from_md
    md = "1. Qual a capital do Brasil?\n2. Quem descobriu o Brasil?"
    qs = _parse_questions_from_md(md)
    assert len(qs) == 2
    assert qs[0]["numero"] == 1
    assert "capital" in qs[0]["texto"]
```

Modelar após os testes de `TestAIProvider` (linhas 244-288).

## Done criteria

ALL must hold:
- [ ] `cd backend && .venv\Scripts\python -m pytest -xvs` exits 0
- [ ] `_parse_questions_from_md` extrai corretamente questões de MarkDown
- [ ] Extrair-texto de PDF não chama DeepSeek quando o parsing simples funciona
- [ ] Fallback para DeepSeek ainda funciona quando parsing falha
- [ ] Nenhum arquivo fora do escopo foi modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Stop and report if:
- O MarkDown gerado pelo MarkItDown não segue padrão de numeração esperado.
- Testes existentes de extrair-texto quebram.

## Maintenance notes

- Se no futuro o MarkItDown mudar o formato de saída, o regex em `_parse_questions_from_md` pode precisar de ajustes.
- O fallback para DeepSeek garante resiliência enquanto o parsing evolui.
