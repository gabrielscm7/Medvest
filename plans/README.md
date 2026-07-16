# Planos de Implementação — Classificação de Questões por IA

Gerado pelo skill improve em 2026-07-16. Executar na ordem abaixo.
Cada executor: ler o plano por completo antes de começar, respeitar as
STOP conditions, e atualizar a linha de status ao concluir.

## Ordem de execução e status

| Plan | Título | Prioridade | Esforço | Depende de | Status |
|------|--------|------------|---------|------------|--------|
| 001 | Backend: extrair texto + classificar questões via IA | P1 | M | — | DONE |
| 002 | Frontend: exibir classificação e permitir confirmação manual | P1 | M | 001 | DONE |
| 003 | Integrar classificação no motor de priorização e dashboard | P2 | S | 001 | DONE |

## Notas de dependência

- 002 requer 001 porque precisa dos endpoints de classificação.
- 003 requer 001 porque precisa dos dados de classificação no banco.

## SHA de referência

Todos os planos foram escritos contra `3446e5f`.
