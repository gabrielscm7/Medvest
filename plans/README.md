# Planos de Implementação

Gerado pelo skill improve em 2026-07-16. Executar na ordem abaixo.
Cada executor: ler o plano por completo antes de começar, respeitar as
STOP conditions, e atualizar a linha de status ao concluir.

## Ordem de execução e status

| Plan | Título | Prioridade | Esforço | Depende de | Status |
|------|--------|------------|---------|------------|--------|
| 001 | Backend: extrair texto + classificar questões via IA | P1 | M | — | DONE |
| 002 | Frontend: exibir classificação e permitir confirmação manual | P1 | M | 001 | DONE |
| 003 | Integrar classificação no motor de priorização e dashboard | P2 | S | 001 | DONE |
| **004** | **Roteamento upload por tipo de arquivo (imagem→Qwen, PDF→MarkItDown)** | **P1** | **M** | **—** | **TODO** |
| **005** | **Otimizar extrair-texto para PDF (parse MD direto, sem LLM re-chamada)** | **P1** | **S** | **004** | **DONE** |
| **006** | **Extração automática de gabarito da última página** | **P1** | **M** | **004** | **DONE** |
| **007** | **Flashcards de questões erradas** | **P1** | **M** | **—** | **TODO** |
| **008** | **Dashboard com gráficos Recharts por área/competência/tema** | **P1** | **M** | **—** | **DONE** |

## Notas de dependência

- 005 depende de 004 porque a otimização do extrair-texto assume que o tipo do arquivo já é detectado no upload.
- 006 depende de 004 porque a extração de gabarito usa `_is_pdf()` e `_is_image()`.
- 007 e 008 são independentes e podem ser executados em paralelo com 004.

## SHA de referência

Todos os planos (004-008) foram escritos contra `570917e`.

## Achados considerados e rejeitados

- **Fix N+1 no dashboard** (joinedload): não virou plano porque o dashboard tem poucos acessos e o impacto real é baixo. Revisitar se houver reclamação de performance.
- **Helpers _ai()/_ocr() duplicados**: baixo impacto, refatoração cosmética. Revisitar quando houver um terceiro router usando o mesmo padrão.
- **CORS allow_origins=["*"]**: deixado como configuração de deploy (Railway), não justifica plano próprio.
- **Silent error handling no classify**: o `try/except continue` intencionalmente pula questões que falham para não travar o lote todo. Melhorar com log em plano futuro se necessário.
