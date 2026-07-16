# Sistema de Preparação ENEM — Foco Medicina
### Plano Pedagógico + Arquitetura Técnica
Preparado para: aluno em preparação intensiva para aprovação em Medicina via ENEM/SiSU
Consultor pedagógico e técnico: Claude (Anthropic)

---

# PARTE 1 — DESENHO PEDAGÓGICO (Analista Educacional)

## 1.1 Premissas do exame (base oficial INEP)

O ENEM é estruturado em **4 áreas de conhecimento**, cada uma com **30 habilidades** (H1–H30) organizadas dentro de competências de área, totalizando **120 habilidades** + a Redação (avaliada por 5 competências próprias):

| Área | Disciplinas | Habilidades | Peso indicativo p/ Medicina (TRI) |
|---|---|---|---|
| Ciências da Natureza | Biologia, Química, Física | 30 (H1–H30) | **Altíssimo** — maior peso relativo na nota de corte de Medicina na maioria das IES via TRI |
| Matemática | Matemática e suas Tecnologias | 30 (H1–H30) | Altíssimo — mesma lógica de TRI, poucos erros derrubam muito a nota |
| Ciências Humanas | História, Geografia, Filosofia, Sociologia | 30 (H1–H30) | Médio-alto (bom custo-benefício: alta taxa de acerto possível) |
| Linguagens | Português, Literatura, Inglês/Espanhol, Artes, Ed. Física, TIC | 30 (H1–H30) | Médio |
| Redação | 5 competências (domínio da norma culta, compreensão do tema, argumentação, coesão, proposta de intervenção) | — | Alto (nota de corte de Medicina normalmente exige redação ≥ 880–920) |

Os **5 eixos cognitivos** comuns a todas as áreas (dominar linguagens, compreender fenômenos, enfrentar situações-problema, construir argumentação, elaborar propostas) devem orientar o *tipo* de questão trabalhada em cada trilha, não só o conteúdo.

**Implicação prática para o sistema**: o conteúdo não deve ser organizado só por "matéria/capítulo" (como um livro didático), mas por **habilidade da matriz**, permitindo relatórios do tipo "aluno domina H12 mas ainda erra 60% de H19". Isso é o diferencial analítico que você quer no painel.

## 1.2 Estrutura de fases (macrociclo)

Modelo de **periodização por fases**, adaptado dos frameworks de Bompa/Issurin que você já usa no esporte (o paralelo funciona bem: base → construção → intensificação → pico/taper → competição):

| Fase | Duração sugerida | Objetivo central | Foco de trilha |
|---|---|---|---|
| **F0 — Diagnóstico** | 1–2 semanas | Mapear ponto de partida | Simulado diagnóstico completo (180 questões) tageado por habilidade; entrevista de metas |
| **F1 — Fundação** | 8–12 semanas | Reconstruir base de conteúdo com lacunas críticas | Trilhas teóricas por competência, volume alto de questões fáceis/médias, foco nas habilidades com pior desempenho no diagnóstico |
| **F2 — Consolidação** | 8–12 semanas | Ampliar cobertura e elevar consistência | Todas as 120 habilidades cobertas; simulados parciais por área a cada 2 semanas |
| **F3 — Intensificação** | 6–8 semanas | Simulados completos, gestão de tempo de prova, redação em série | Simulados cronometrados completos semanais; foco em habilidades ainda fracas (retreino direcionado) |
| **F4 — Polimento/Taper** | 2–3 semanas antes da prova | Reduzir volume, manter afiação, cuidar de saúde mental e sono | Revisão ativa (flashcards/erros antigos), redução de carga, 1 simulado leve por semana |
| **F5 — Prova e pós-prova** | Dias da prova + revisão | Execução | — |

Cada fase gera automaticamente as **trilhas da semana** com base no desempenho real do aluno (adaptativo), não num cronograma fixo e genérico.

## 1.3 Trilhas de aprendizagem (estrutura de dados pedagógica)

Hierarquia: **Área → Competência → Habilidade → Objeto de conhecimento → Questão**

Cada **trilha** é uma sequência ordenada de:
1. Microaula/resumo teórico (texto ou vídeo externo curado, ex. YouTube educacional já existente — não precisa ser produzido do zero)
2. Bateria de questões-treino (10–15 questões) daquela habilidade, por nível de dificuldade crescente
3. Checkpoint (mini simulado de 5 questões misturando habilidades já vistas — retenção espaçada)
4. Métrica de domínio: % de acerto + tempo médio por questão

O sistema recalcula automaticamente a **prioridade da trilha** usando uma fórmula simples de priorização (pode rodar em um job noturno):

```
prioridade(habilidade) =
    peso_area(habilidade)          # normatizado pela relevância p/ Medicina
  * (1 - taxa_acerto_recente)      # quanto pior o aluno vai, maior a prioridade
  * fator_recencia                 # habilidades não vistas há muito tempo sobem na fila (repetição espaçada)
  * fator_incidencia_historica     # frequência da habilidade nas provas ENEM anteriores
```

Isso é o "algoritmo adaptativo" — nada de IA complexa é necessário no início; é uma fórmula ponderada, auditável, e você pode calibrar os pesos manualmente com sua experiência.

## 1.4 Metas diárias e semanais

**Meta diária (padrão sugerido, ajustável por fase):**
- 1 trilha de conteúdo (30–45 min)
- 20–30 questões (dividido entre reforço de fraquezas e manutenção de fortalezas — proporção 70/30)
- 1 bloco de redação por semana (não diário) nas fases F1–F3; 2x/semana na F3–F4
- Registro de sono/energia (1 clique, 3 opções) — dado leve, mas correlaciona muito com desempenho e ajuda você como profissional de treinamento a cruzar variáveis

**Meta semanal:**
- Cobertura mínima: todas as 4 áreas tocadas pelo menos 3x na semana (evita "efeito gargalo" de estudar só o que gosta)
- 1 simulado parcial (60–90 questões) a partir da F2
- Revisão de erros da semana anterior (sessão dedicada de 30–45 min "revisão de erros", que é onde o ganho de nota realmente acontece)
- Relatório automático enviado (e-mail ou WhatsApp, dado seu histórico com HealthReport) resumindo desempenho da semana

## 1.5 Banco de questões — estratégia de conteúdo

Como não há integração via API com o Estratégia Vestibulares, a estratégia recomendada é híbrida:

1. **Banco próprio a partir de fontes oficiais e abertas**: o INEP disponibiliza gratuitamente, em `download.inep.gov.br`, todas as provas e gabaritos do ENEM desde 2009 (formato PDF/dados abertos), além dos microdados com o índice de dificuldade/discriminação de cada item (parâmetros de TRI). Isso permite:
   - Importar as questões oficiais (texto, sem violar direitos de imagem/terceiros incorporados — atenção a textos de apoio com direitos autorais de terceiros, que exigem citação e não republicação integral indiscriminada)
   - Tagueá-las manualmente (ou semi-automaticamente) por habilidade, competência e área
   - Usar os parâmetros de TRI reais como "peso de dificuldade" nas suas questões — ganho enorme de qualidade analítica
2. **Questões autorais complementares**: para aumentar volume nas habilidades mais fracas, você (ou colaboradores) cria questões próprias no estilo ENEM, tageadas desde a criação.
3. **Estratégia Vestibulares como banco paralelo, não integrado**: o aluno resolve lá normalmente, mas o *registro* de desempenho daquele banco fica fora do seu sistema, a menos que o aluno digite manualmente os resultados (pode-se criar uma tela simples de "lançamento manual de simulado externo" para não perder o dado). Se no futuro a Estratégia lançar uma API B2B ou parceria, aí sim dá para automatizar — vale a pena, em algum momento, mandar um e-mail para o setor comercial deles perguntando sobre isso; cursinhos grandes às vezes têm parcerias com escolas/preparadores.

## 1.6 Painel de acompanhamento (visão pedagógica, antes da tela)

O painel deve responder, na ordem que o aluno olha:
1. **"Estou no caminho para a nota que preciso?"** → gráfico de evolução da nota estimada (TRI simulada) vs. nota de corte histórica de Medicina da instituição-alvo
2. **"Onde estou perdendo pontos?"** → heatmap de habilidades (120 células, cor por % de acerto)
3. **"O que fazer hoje?"** → a trilha do dia, já calculada
4. **"Estou cumprindo o combinado?"** → streak de dias de estudo, aderência à meta semanal
5. **Comparativo temporal**: últimas 4 semanas, por área

---

# PARTE 2 — ARQUITETURA TÉCNICA (Desenvolvedor Sênior)

## 2.1 Stack recomendada

Dado que você já opera com sucesso **FastAPI + PostgreSQL + Redis no Railway** (HealthReport) e já resolveu as dores de deploy típicas (migrations, enums SQLAlchemy, static files), vou manter a mesma stack para reaproveitar sua curva de aprendizado e infra já validada:

- **Backend**: FastAPI (Python) + SQLAlchemy + Alembic (migrations)
- **Banco**: PostgreSQL (Railway managed)
- **Cache/filas**: Redis (cálculo de prioridade de trilhas, jobs assíncronos, rate limiting)
- **Worker assíncrono**: Celery ou RQ (mais leve — recomendo RQ dado o porte do projeto) para: recalcular prioridades à noite, gerar relatórios semanais, processar importação de provas
- **Frontend**: React + Vite (ou Vanilla JS se quiser manter simplicidade do HealthReport) + Chart.js/Recharts para os gráficos
- **Auth**: JWT (mesmo padrão do DocFinance que você já validou)
- **Hospedagem**: Railway (Postgres + Redis + Web service, 3 serviços no mesmo projeto)
- **Notificações**: WhatsApp (via API oficial/Twilio) ou e-mail transacional (Resend/SendGrid) para o relatório semanal — dado seu histórico com HealthReport usando WhatsApp como interface, faz sentido replicar aqui para lembretes diários

## 2.2 Modelagem de dados (núcleo)

```sql
-- Estrutura da matriz de referência (dado semi-estático, carregado 1x)
CREATE TABLE area (
    id SERIAL PRIMARY KEY,
    nome VARCHAR NOT NULL,          -- 'Ciências da Natureza', etc.
    peso_medicina NUMERIC DEFAULT 1.0
);

CREATE TABLE competencia (
    id SERIAL PRIMARY KEY,
    area_id INTEGER REFERENCES area(id),
    numero INTEGER,
    descricao TEXT
);

CREATE TABLE habilidade (
    id SERIAL PRIMARY KEY,
    competencia_id INTEGER REFERENCES competencia(id),
    codigo VARCHAR NOT NULL,        -- 'H12'
    descricao TEXT,
    incidencia_historica NUMERIC DEFAULT 0  -- frequência em provas passadas
);

-- Banco de questões
CREATE TABLE questao (
    id SERIAL PRIMARY KEY,
    habilidade_id INTEGER REFERENCES habilidade(id),
    origem VARCHAR,                 -- 'ENEM_OFICIAL_2019', 'AUTORAL'
    ano INTEGER,
    enunciado TEXT,
    alternativas JSONB,             -- {"A": "...", "B": "...", ...}
    gabarito VARCHAR(1),
    dificuldade_tri NUMERIC,        -- parâmetro b do ITEM (se disponível via microdados)
    discriminacao_tri NUMERIC,      -- parâmetro a
    ativa BOOLEAN DEFAULT TRUE
);

-- Aluno e desempenho
CREATE TABLE aluno (
    id SERIAL PRIMARY KEY,
    nome VARCHAR,
    email VARCHAR UNIQUE,
    meta_instituicao VARCHAR,       -- p.ex. 'UFSCar Medicina'
    data_prova DATE,
    senha_hash VARCHAR,
    criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE tentativa_questao (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER REFERENCES aluno(id),
    questao_id INTEGER REFERENCES questao(id),
    correta BOOLEAN,
    tempo_segundos INTEGER,
    contexto VARCHAR,               -- 'trilha', 'simulado', 'lancamento_manual'
    criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE dominio_habilidade (
    aluno_id INTEGER REFERENCES aluno(id),
    habilidade_id INTEGER REFERENCES habilidade(id),
    taxa_acerto NUMERIC,
    ultima_pratica TIMESTAMP,
    prioridade_calculada NUMERIC,
    PRIMARY KEY (aluno_id, habilidade_id)
);

CREATE TABLE simulado (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER REFERENCES aluno(id),
    tipo VARCHAR,                   -- 'diagnostico', 'parcial', 'completo'
    nota_estimada NUMERIC,
    data_realizacao TIMESTAMP,
    duracao_minutos INTEGER
);

CREATE TABLE trilha_diaria (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER REFERENCES aluno(id),
    data DATE,
    habilidades_alvo INTEGER[],     -- array de habilidade_id priorizadas
    concluida BOOLEAN DEFAULT FALSE
);

CREATE TABLE registro_bem_estar (
    aluno_id INTEGER REFERENCES aluno(id),
    data DATE,
    sono VARCHAR,                   -- 'ruim','ok','bom'
    energia VARCHAR,
    PRIMARY KEY (aluno_id, data)
);
```

## 2.3 Módulos do sistema

1. **Auth & perfil** — JWT, cadastro do aluno, meta de instituição/curso, data da prova (para contagem regressiva)
2. **Motor de trilhas** — job assíncrono (roda 1x/dia via RQ scheduler) que recalcula `prioridade_calculada` por habilidade e monta a `trilha_diaria`
3. **Banco de questões / importador**
   - Script de importação dos PDFs oficiais do INEP (extração de texto + segmentação por questão — pode usar `pdfplumber`/`PyMuPDF`)
   - Tela administrativa simples para revisar e tagear cada questão importada por habilidade (import assistido, não 100% automático — a tageação de habilidade exige julgamento humano na maior parte dos casos)
   - Cadastro de questões autorais
4. **Motor de simulados** — monta prova cronometrada (180 questões completas ou parciais), calcula nota estimada (pode usar uma estimativa simplificada de TRI, ou uma escala linear no MVP e evoluir depois)
5. **Dashboard/analytics** (o coração do pedido)
   - Heatmap de habilidades (120 células) — Recharts/D3
   - Linha de evolução da nota estimada por simulado, com linha de referência da nota de corte
   - Gráfico de pizza/barra: distribuição de acertos por área
   - Streak / aderência à meta semanal
   - Exportação de relatório semanal em PDF (reaproveitando padrão que você já usa nos seus relatórios de treino)
6. **Notificações** — job diário que dispara lembrete da trilha do dia e, semanalmente, o relatório consolidado

## 2.4 Fluxo de prioridade calculada (pseudocódigo do job noturno)

```python
def recalcular_prioridades(aluno_id):
    for habilidade in todas_habilidades():
        tentativas = get_tentativas_recentes(aluno_id, habilidade.id, dias=21)
        taxa_acerto = calcular_taxa(tentativas) if tentativas else 0.5  # neutro se nunca praticou
        dias_desde_ultima = calcular_recencia(tentativas)
        fator_recencia = min(dias_desde_ultima / 14, 2.0)  # cresce até 14 dias, depois satura
        prioridade = (
            habilidade.area.peso_medicina
            * (1 - taxa_acerto)
            * fator_recencia
            * (1 + habilidade.incidencia_historica)
        )
        salvar_dominio_habilidade(aluno_id, habilidade.id, taxa_acerto, prioridade)

    top_habilidades = get_top_n_por_prioridade(aluno_id, n=4)
    montar_trilha_diaria(aluno_id, top_habilidades)
```

## 2.5 Roadmap de construção (fases de desenvolvimento — MVP até V2)

| Sprint | Entregável |
|---|---|
| **1** | Modelagem do banco + seed da matriz de referência (120 habilidades) + auth básico |
| **2** | Importador de provas oficiais ENEM (2015–2025) + tela de tageação manual |
| **3** | Motor de trilha diária (regra de prioridade simples, sem job assíncrono ainda) + tela do aluno para responder questões |
| **4** | Dashboard v1: heatmap + evolução de nota + gráficos básicos |
| **5** | Motor de simulados completos cronometrados + cálculo de nota estimada |
| **6** | Jobs assíncronos (Redis + RQ), notificações por e-mail/WhatsApp, relatório semanal em PDF |
| **7** | Módulo de redação (upload de texto/foto, correção manual sua com rubrica das 5 competências, histórico de notas de redação) |
| **8 (V2)** | Refinamento do algoritmo de prioridade com dados reais acumulados; possível parceria/API com Estratégia Vestibulares se surgir oportunidade comercial |

## 2.6 Considerações de deploy no Railway (com base na sua experiência anterior)

- 3 serviços no mesmo projeto Railway: `web` (FastAPI), `postgres` (managed), `redis` (managed)
- Alembic rodando como *release command* antes do boot do serviço web, para evitar os erros de migration que você já enfrentou no HealthReport
- Cuidado redobrado com **enums do SQLAlchemy** (mesmo ponto de dor do projeto anterior) — recomendo usar `VARCHAR` + `CHECK constraint` em vez de enum nativo do Postgres, é mais tolerante a mudanças futuras sem migration complexa
- Servir o frontend como build estático (se React) via Nginx/Caddy simples ou dentro do próprio FastAPI com `StaticFiles`, replicando a solução que você já validou

---

## Próximos passos possíveis
Posso, a partir daqui:
1. Já montar o **scaffold real do backend** (FastAPI + models + Alembic) pronto para rodar no Railway
2. Escrever o **script de importação das provas oficiais do INEP** (baixar, extrair, estruturar)
3. Criar um **protótipo do dashboard** (React) com dados fictícios para você validar visualmente antes de plugar no backend

Me diga por qual desses você quer começar.
