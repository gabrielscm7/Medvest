# Plan 008: Dashboard com gráficos por área, competência e tema (Recharts)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 570917e..HEAD -- backend/app/routers/dashboard.py backend/app/schemas/dashboard.py backend/app/services/ frontend/src/pages/Dashboard.tsx frontend/src/api/dashboard.ts`
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

O dashboard hoje mostra apenas um heatmap textual das 120 habilidades e cards de métricas. Não há nenhum gráfico visual. O Recharts (`recharts@^3.9.2`) já está instalado no frontend (`frontend/package.json:18`) mas nunca é usado. A adição de gráficos por área (ex: "Ciências da Natureza"), competência (ex: "Competência 1 - Biologia") e tema_livre permitirá ao aluno visualizar rapidamente onde estão seus pontos fracos.

## Current state

- `backend/app/routers/dashboard.py:21-90` — endpoint `GET /api/dashboard/` retorna:
  - `heatmap: list[HabilidadeHeatmap]` — lista plana de habilidades com taxa_acerto
  - `plano_temporal`, métricas numéricas
  - Sem agregação por área, competência ou tema_livre

- `backend/app/schemas/dashboard.py:1-38` — schemas existentes. Precisa de novos campos.
- `frontend/src/pages/Dashboard.tsx` — renderiza cards + lista textual de habilidades. Não importa Recharts.
- `frontend/src/api/dashboard.ts` — tipagem `Dashboard` sem dados de gráfico.

## Commands you will need

| Purpose   | Command                                                | Expected on success |
|-----------|--------------------------------------------------------|---------------------|
| Backend   | `cd backend && .venv\Scripts\python -m pytest -xvs`   | all pass            |
| Frontend  | `cd frontend && npm run build`                         | exit 0              |
| Frontend  | `cd frontend && npm run lint`                          | exit 0              |

## Scope

**In scope**:
- `backend/app/routers/dashboard.py`
- `backend/app/schemas/dashboard.py`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/api/dashboard.ts`

**Out of scope**:
- `backend/app/models.py` — não alterar schema do banco
- `backend/app/services/prioritization.py` — não alterar lógica de priorização
- Outras páginas do frontend

## Git workflow

- Branch: `advisor/008-dashboard-graficos`
- Commits: backend first, then frontend
- Estilo: `feat: adicionar gráficos de área/competência/tema no dashboard`

## Steps

### Step 1: Adicionar campos agregados no schema do dashboard

Em `backend/app/schemas/dashboard.py`, adicione:

```python
class AreaChartData(BaseModel):
    nome: str
    taxa_acerto: float
    peso_medicina: float
    total_questoes: int

class CompetenciaChartData(BaseModel):
    area_nome: str
    competencia_numero: int
    descricao: str
    taxa_acerto: float
    total_questoes: int

class TemaChartData(BaseModel):
    tema: str
    area_nome: str
    taxa_acerto: float
    total_questoes: int
```

E no `DashboardResponse`, adicione:

```python
    graficos_area: list[AreaChartData] = []
    graficos_competencia: list[CompetenciaChartData] = []
    graficos_tema: list[TemaChartData] = []
```

### Step 2: Calcular agregações no endpoint dashboard

Em `backend/app/routers/dashboard.py`, no fim do `dashboard()`, antes do `return`, adicione:

```python
    # Agregação por Área
    areas = db.query(Area).all()
    graficos_area = []
    for area in areas:
        questoes_area = (
            db.query(QuestaoIdentificada)
            .join(QuestaoIdentificada.simulado_upload)
            .join(QuestaoIdentificada.habilidade)
            .join(Habilidade.competencia)
            .filter(
                SimuladoUpload.aluno_id == aluno.id,
                Competencia.area_id == area.id,
                QuestaoIdentificada.acerto.isnot(None),
            )
            .all()
        )
        total = len(questoes_area)
        acertos = sum(1 for q in questoes_area if q.acerto)
        taxa = acertos / total if total > 0 else 0.0
        graficos_area.append(AreaChartData(
            nome=area.nome,
            taxa_acerto=round(taxa, 2),
            peso_medicina=float(area.peso_medicina),
            total_questoes=total,
        ))

    # Agregação por Competência
    graficos_competencia = []
    for area in areas:
        for comp in area.competencias:
            questoes_comp = (
                db.query(QuestaoIdentificada)
                .join(QuestaoIdentificada.simulado_upload)
                .join(QuestaoIdentificada.habilidade)
                .filter(
                    SimuladoUpload.aluno_id == aluno.id,
                    Habilidade.competencia_id == comp.id,
                    QuestaoIdentificada.acerto.isnot(None),
                )
                .all()
            )
            total = len(questoes_comp)
            acertos = sum(1 for q in questoes_comp if q.acerto)
            taxa = acertos / total if total > 0 else 0.0
            graficos_competencia.append(CompetenciaChartData(
                area_nome=area.nome,
                competencia_numero=comp.numero,
                descricao=comp.descricao[:80],
                taxa_acerto=round(taxa, 2),
                total_questoes=total,
            ))

    # Agregação por Tema Livre (tema_livre)
    temas_counts: dict[str, dict] = {}
    questoes_com_tema = (
        db.query(QuestaoIdentificada)
        .join(QuestaoIdentificada.simulado_upload)
        .filter(
            SimuladoUpload.aluno_id == aluno.id,
            QuestaoIdentificada.tema_livre.isnot(None),
            QuestaoIdentificada.acerto.isnot(None),
        )
        .all()
    )
    for q in questoes_com_tema:
        tema = q.tema_livre or "sem tema"
        if tema not in temas_counts:
            temas_counts[tema] = {"total": 0, "acertos": 0, "area": ""}
        temas_counts[tema]["total"] += 1
        if q.acerto:
            temas_counts[tema]["acertos"] += 1
        if q.habilidade and q.habilidade.competencia and q.habilidade.competencia.area:
            temas_counts[tema]["area"] = q.habilidade.competencia.area.nome

    graficos_tema = [
        TemaChartData(
            tema=tema,
            area_nome=data["area"],
            taxa_acerto=round(data["acertos"] / data["total"], 2) if data["total"] > 0 else 0.0,
            total_questoes=data["total"],
        )
        for tema, data in sorted(temas_counts.items(), key=lambda x: x[1]["total"], reverse=True)
    ]
```

E no `return DashboardResponse(...)`, adicione os novos campos:

```python
    graficos_area=graficos_area,
    graficos_competencia=graficos_competencia,
    graficos_tema=graficos_tema,
```

**Verify**:
```
cd backend && .venv\Scripts\python -m pytest -xvs -k "test_dashboard"
```
→ Teste passa.

### Step 3: Atualizar tipos no frontend

Em `frontend/src/api/dashboard.ts`, adicione:

```typescript
export interface AreaChartData {
  nome: string;
  taxa_acerto: number;
  peso_medicina: number;
  total_questoes: number;
}

export interface CompetenciaChartData {
  area_nome: string;
  competencia_numero: number;
  descricao: string;
  taxa_acerto: number;
  total_questoes: number;
}

export interface TemaChartData {
  tema: string;
  area_nome: string;
  taxa_acerto: number;
  total_questoes: number;
}

// Adicione no Dashboard:
export interface Dashboard {
  // ... existing fields
  graficos_area: AreaChartData[];
  graficos_competencia: CompetenciaChartData[];
  graficos_tema: TemaChartData[];
}
```

### Step 4: Adicionar gráficos Recharts no Dashboard.tsx

No topo de `frontend/src/pages/Dashboard.tsx`, adicione imports:

```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
```

Após o bloco "Questões Respondidas" (após a linha 104), adicione:

```tsx
      {/* Gráfico por Área */}
      {data?.graficos_area && data.graficos_area.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Taxa de Acerto por Área</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.graficos_area}>
              <XAxis dataKey="nome" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
              <Bar dataKey="taxa_acerto" fill="#059669" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Gráfico por Tema */}
      {data?.graficos_tema && data.graficos_tema.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Distribuição por Tema</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data.graficos_tema}
                dataKey="total_questoes"
                nameKey="tema"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ tema, percent }) => `${tema} (${(percent * 100).toFixed(0)}%)`}
              >
                {data.graficos_tema.map((_, i) => (
                  <Cell key={i} fill={['#059669', '#2563eb', '#d97706', '#dc2626', '#7c3aed', '#db2777', '#0891b2', '#65a30d'][i % 8]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Gráfico por Competência (top 10) */}
      {data?.graficos_competencia && data.graficos_competencia.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Competências (Top 10)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.graficos_competencia.slice(0, 10)} layout="vertical">
              <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <YAxis type="category" dataKey="descricao" width={200} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
              <Bar dataKey="taxa_acerto" fill="#2563eb" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
```

**Verify**:
```
cd frontend && npm run build
```
→ Build succeeds, sem erros de tipo.

## Test plan

Backend:
- O teste `test_dashboard` (linha 180-188) já testa o endpoint. Adicione verificação dos novos campos:
  ```python
  assert "graficos_area" in data
  assert "graficos_competencia" in data
  assert "graficos_tema" in data
  ```

Frontend:
- `npm run build` compila sem erros. Teste visual: abrir o dashboard e verificar se os gráficos renderizam.

## Done criteria

ALL must hold:
- [ ] `cd backend && .venv\Scripts\python -m pytest -xvs` exits 0
- [ ] `cd frontend && npm run build` exits 0
- [ ] Dashboard exibe gráfico de barras por Área
- [ ] Dashboard exibe gráfico de pizza por Tema
- [ ] Dashboard exibe gráfico de barras horizontal por Competência (top 10)
- [ ] Nenhum arquivo fora do escopo foi modificado
- [ ] `plans/README.md` status row atualizado

## STOP conditions

Stop and report if:
- `npm run build` falha por erro de tipo — TypeScript 6.0 é estrito, verifique se os tipos no `dashboard.ts` estão corretos
- Recharts não está disponível (verificar `node_modules`)

## Maintenance notes

- As queries de agregação disparam várias consultas (uma por área/competência). Para dashboards de alunos com muitos simulados, considere cache ou uma query agregada única.
- As cores dos gráficos de pizza usam um array fixo; se houver mais de 8 temas, cores se repetem. Expanda o array se necessário.
