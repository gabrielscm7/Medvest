# Plano 003: Integrar classificações no motor de priorização e dashboard

> **Instruções ao executor**: Siga este plano passo a passo. Execute cada
> comando de verificação e confirme o resultado esperado antes de avançar.
> Se algo nas "STOP conditions" ocorrer, PARE e reporte — não improvise.
> Ao finalizar, atualize a linha de status em `plans/README.md`.
>
> **Drift check (execute primeiro)**: `git diff --stat 3446e5f..HEAD -- backend/app/services/prioritization.py backend/app/routers/dashboard.py`
> Se algum arquivo in-scope mudou desde o SHA do plano, compare os
> trechos de "Current state" com o código atual antes de prosseguir;
> em caso de divergência, trate como STOP condition.

## Status

- **Prioridade**: P2
- **Esforço**: S
- **Risco**: LOW
- **Depende de**: 001
- **Categoria**: tech-debt
- **Planned at**: commit `3446e5f`, 2026-07-16

## Por que isso importa

O motor de priorização (plano 001 já chama `recalcular_prioridades` após
classificar) e o dashboard usam os dados de `DominioHabilidade`. Mas antes
deste plano, as classificações nunca eram salvas — então `DominioHabilidade`
só tinha dados se houvesse seed manual. Depois do plano 001, as questões
classificadas alimentam `DominioHabilidade`. Este plano garante que o
dashboard mostre os dados corretos e que o recálculo de prioridades seja
disparado automaticamente quando novas classificações chegarem.

## Estado atual

- `backend/app/services/prioritization.py` — `recalcular_prioridades()`
  já existe. Precisa ser chamado após classificar (plano 001 já faz isso).

- `backend/app/routers/dashboard.py` — endpoint `GET /api/dashboard` que
  calcula métricas. Provavelmente já funciona porque usa
  `DominioHabilidade` que é populado por `recalcular_prioridades`.

- `backend/app/routers/simulados.py` — plano 001 já adicionou chamada a
  `recalcular_prioridades` dentro do endpoint `POST /{id}/classificar`.

**O que falta**: Nada estrutural — a integração já foi feita no plano 001.
Este plano é de **verificação** + pequenos ajustes.

## Escopo

**In scope**:
- `backend/app/services/prioritization.py` — revisar se o recálculo
  está correto e adicionar trigger para ser chamado também ao criar
  `DominioHabilidade` pela primeira vez.
- `backend/app/routers/dashboard.py` — verificar se o dashboard
  já reflete as classificações corretamente.

**Out of scope**:
- Frontend do dashboard (já funciona)
- Algoritmo de priorização em si (já foi validado)

## Passos

### Passo 1: Verificar que `recalcular_prioridades` está sendo chamado

Leia `backend/app/services/prioritization.py` e confirme que a função
aceita `db: Session` e `aluno_id: int` e recalcula corretamente.

Se não existir trigger automático, adicione no endpoint `POST /{id}/gabarito`
também — pois quando o aluno preenche o gabarito, os campos `acerto` são
populados, e a prioridade deve refletir isso independente da classificação.

Adicione no final de `preencher_gabarito` em `backend/app/routers/simulados.py`,
antes do `return`:
```python
from app.services.prioritization import recalcular_prioridades
recalcular_prioridades(db, aluno.id)
```

**Verifique**: `cd backend; python -c "from app.services.prioritization import recalcular_prioridades; print('OK')"` → OK

### Passo 2: Verificar dashboard

Leia `backend/app/routers/dashboard.py` e `backend/app/schemas/dashboard.py`.
Confirme que as métricas usam `DominioHabilidade` e que os cálculos estão
corretos.

Se o dashboard não estiver filtrando corretamente as habilidades com
classificação vs sem classificação, ajuste.

**Verifique**: `curl -X GET http://localhost:8000/api/dashboard` com token
válido → retorna 200 com métricas populadas

### Passo 3: Adicionar endpoint `GET /api/habilidades`

Para o plano 002 (modal de confirmação manual) e para o dashboard, é útil
ter um endpoint que lista todas as habilidades.

Adicione em `backend/app/routers/simulados.py` (ou crie `backend/app/routers/habilidades.py`):

```python
from app.models import Habilidade, Competencia, Area

@router.get("/habilidades", response_model=list[HabilidadeResponse])
def listar_habilidades(db: Session = Depends(get_db)):
    return db.query(Habilidade).order_by(Habilidade.codigo).all()
```

Crie `HabilidadeResponse` em `backend/app/schemas/simulado.py`:
```python
class HabilidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    descricao: str
```

**Importante**: Se criar um router separado, registre em `backend/app/main.py`.

**Verifique**: `curl http://localhost:8000/api/habilidades` → array com 120 habilidades

## Plano de teste

Teste funcional:
1. Faça upload de simulado
2. Classifique questões
3. Verifique GET /api/dashboard → taxa_acerto_geral, heatmap populados
4. Verifique GET /api/habilidades → 120 habilidades retornadas

## Done criteria

- [ ] `recalcular_prioridades` é chamado após preencher gabarito
- [ ] Dashboard reflete classificações recém-calculadas
- [ ] `GET /api/habilidades` retorna lista de habilidades
- [ ] `cd backend; pytest . -v` passa
- [ ] `plans/README.md` atualizado

## STOP conditions

Pare e reporte se:
- O algoritmo de priorização em `prioritization.py` for diferente do esperado
- O dashboard tiver dependências não documentadas

## Notas de manutenção

- O endpoint de habilidades é usado pelo frontend (plano 002) para o
  modal de confirmação manual. Se o modal evoluir para um searchable
  dropdown, o endpoint continuará servindo.
