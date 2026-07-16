# Sistema de Preparação ENEM — Medicina
## Especificação do Projeto — v3 (consolidada)
Aluno-alvo: preparação intensiva para ENEM/SiSU com foco em Medicina
Data de referência: 15/07/2026 | Prova: 08/11/2026 (dia 1) e 15/11/2026 (dia 2)

---

## Changelog de versões

| Versão | Mudança principal |
|---|---|
| v1 | Concepção inicial: banco de questões nativo importado do INEP, trilhas fixas por fase |
| v2 | Remoção do banco nativo; leitura de simulados via upload + OCR/IA; redação via OCR + correção por IA; planejamento temporal dinâmico até as datas de prova |
| **v3 (atual)** | Matriz de referência oficial importada e estruturada (JSON); ficha de gabarito 100% virtual com **autodetecção** de nº de questões/alternativas; provedor de IA definido como **DeepSeek V4**, com camada de abstração e fallback de visão |

---

## 1. Visão geral do sistema

Plataforma web (acessível pela internet, hospedada no Railway) que:
- **Não possui banco de questões próprio.** Todo o conteúdo avaliativo vem de simulados que o aluno já faz por conta própria (papel, Estratégia Vestibulares, cadernos de cursinho, provas oficiais antigas, etc.)
- Lê esses simulados via upload de imagens/PDF, usando IA multimodal para identificar a estrutura da prova e classificar cada questão pela **Matriz de Referência oficial do ENEM**
- Faz correção assistida de redação (OCR + rubrica das 5 competências oficiais)
- Gera automaticamente um **guia semanal de estudos** (trilhas priorizadas) e sessões de revisão/flashcards, adaptando-se ao desempenho real e ao tempo restante até a prova
- Apresenta um painel visual de evolução (heatmap de habilidades, gráficos de acerto/erro, nota estimada)

---

## 2. Fundamentação pedagógica

### 2.1 Base oficial (matriz de referência, já importada e estruturada)

Confirmado a partir do documento oficial fornecido — estrutura validada, 120 habilidades no total:

| Área | Competências | Habilidades |
|---|---|---|
| Linguagens, Códigos e suas Tecnologias | 9 | 30 (H1–H30) |
| Matemática e suas Tecnologias | 7 | 30 (H1–H30) |
| Ciências da Natureza e suas Tecnologias | 8 | 30 (H1–H30) |
| Ciências Humanas e suas Tecnologias | 6 | 30 (H1–H30) |
| **Redação** | 5 competências próprias (C1–C5, 0–200 cada) | — |

5 eixos cognitivos comuns a todas as áreas: Dominar Linguagens, Compreender Fenômenos, Enfrentar Situações-Problema, Construir Argumentação, Elaborar Propostas.

Já entreguei o arquivo `matriz_estruturada.json` com toda essa hierarquia parseada (área → competência → habilidade → descrição oficial), pronto para popular o banco de dados sem risco de erro de digitação/interpretação.

### 2.2 Fases do macrociclo (recalculadas dinamicamente)

O sistema não usa durações fixas de fase — ele recalcula a divisão de semanas restantes toda vez que um novo simulado é processado, com base em:
- Data de hoje → 08/11/2026 (semanas totais disponíveis)
- Nível médio de acerto diagnosticado do aluno (extraído dos simulados já processados)

| Fase | Foco |
|---|---|
| F1 — Fundação | Reconstrução de base nas habilidades mais fracas |
| F2 — Consolidação | Cobertura das 120 habilidades, simulados parciais |
| F3 — Intensificação | Simulados completos cronometrados, gestão de tempo de prova |
| F4 — Polimento (últimas semanas) | Revisão ativa, redução de carga, cuidado com sono/energia |

**Regra especial das duas datas de prova**: a janela entre 08/11 e 15/11 é automaticamente realocada como sprint focado em Matemática e Ciências da Natureza (dia 2 da prova), por serem historicamente as áreas de maior peso na nota de corte de Medicina.

### 2.3 Metas diárias e semanais

- Diária: 1 trilha de revisão/flashcards + registro rápido de sono/energia (1 clique)
- Semanal: pelo menos 1 simulado processado pelo sistema (a partir da F2) + sessão de revisão de erros + 1 redação (2x/semana a partir da F3)
- Todas as metas são recalculadas em função da carga de estudo definida pelo nível diagnosticado (ver fórmula na seção 4.2)

---

## 3. Fluxos funcionais

### 3.1 Motor de leitura de simulados (núcleo do sistema)

```
1. Aluno faz upload do caderno de prova (fotos/PDF)
        ↓
2. IA (visão) varre as páginas e detecta automaticamente:
   - quantidade total de questões
   - nº de alternativas por questão (4 ou 5, pode variar por caderno)
   - numeração inicial (nem sempre começa em 1)
        ↓
3. Sistema gera dinamicamente a tela de preenchimento
   (grade de botões por questão, com as alternativas certas para cada uma)
        ↓
4. Aluno marca suas respostas na tela (clique, não digitação)
        ↓
5. Aluno informa o gabarito oficial (campo de texto simples, ex: "1-C,2-A,3-E...")
        ↓
6. IA (visão/texto) processa o conteúdo de cada questão do caderno e classifica:
   área → competência → habilidade → tema livre → dificuldade estimada
   (usando a matriz de referência como grounding)
        ↓
7. Sistema cruza resposta_aluno x gabarito_oficial x classificação
   → acerto/erro por questão, agregado por habilidade/competência/área
        ↓
8. Atualiza domínio de habilidade do aluno + recalcula prioridades
        ↓
9. Gera/atualiza o guia da semana e o painel
```

Interface mostra a classificação sugerida por questão com opção de correção manual em 1 toque (o aluno confirma ou ajusta a habilidade sugerida) — isso também serve de dado de calibração ao longo do tempo.

### 3.2 Redação

```
1. Upload de foto/scan do texto (manuscrito ou digitado)
2. IA faz OCR/transcrição
3. IA aplica a rubrica oficial das 5 competências do ENEM (C1-C5, 0-200 cada)
4. Retorno: nota por competência + nota total (0-1000) + feedback específico por competência
5. Histórico evolutivo (gráfico de linha, 1 série por competência)
```
Aviso na interface: nota da IA é estimativa de treino, não substitui avaliação humana — recomendado calibrar periodicamente com revisão manual sua.

### 3.3 Revisão inteligente e flashcards

- Sem banco fixo: flashcards são **gerados sob demanda pela IA**, direcionados às habilidades priorizadas, usando a descrição oficial da habilidade/competência como grounding e o histórico de erros do aluno para calibrar dificuldade
- Repetição espaçada tipo SM-2 (Anki): acerto aumenta o intervalo pelo fator de facilidade; erro reinicia o ciclo
- Sessão semanal de revisão mistura flashcards vencidos + 1-2 questões novas geradas pela IA nas habilidades mais fracas (uso didático, descartável, não vira "banco")

---

## 4. Motor de priorização e planejamento

### 4.1 Fórmula de prioridade por habilidade
```
prioridade(habilidade) =
    peso_area_medicina(habilidade)
  * (1 - taxa_acerto_recente)
  * fator_recencia          # cresce até ~14 dias sem prática, depois satura
  * fator_incidencia_historica
```
Recalculada a cada novo simulado processado. Gera a lista de 3-5 habilidades prioritárias da semana.

### 4.2 Planejamento temporal dinâmico
```python
def recalcular_macrociclo(aluno):
    dias_ate_dia1 = (date(2026, 11, 8) - date.today()).days
    semanas_totais = dias_ate_dia1 // 7
    nivel_medio = media_taxa_acerto_geral(aluno)

    if nivel_medio < 0.4:
        distrib = {"F1": 0.45, "F2": 0.30, "F3": 0.20, "F4": 0.05}
        carga_diaria_questoes = 35
    elif nivel_medio < 0.65:
        distrib = {"F1": 0.30, "F2": 0.35, "F3": 0.25, "F4": 0.10}
        carga_diaria_questoes = 25
    else:
        distrib = {"F1": 0.10, "F2": 0.30, "F3": 0.40, "F4": 0.20}
        carga_diaria_questoes = 20

    return {f: max(1, round(p * semanas_totais)) for f, p in distrib.items()}, carga_diaria_questoes
```

---

## 5. Painel de acompanhamento

1. Evolução da nota estimada vs. nota de corte histórica da instituição-alvo
2. Heatmap das 120 habilidades por taxa de acerto
3. Trilha/tarefas do dia
4. Streak de estudo e aderência à meta semanal
5. Comparativo por área nas últimas 4 semanas
6. Evolução da redação por competência (C1-C5)

---

## 6. Arquitetura técnica

### 6.1 Stack
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Banco**: PostgreSQL (Railway managed)
- **Fila assíncrona**: Redis + RQ — processa uploads (OCR/classificação) em background, aluno recebe notificação quando pronto
- **Storage de arquivos**: bucket externo compatível S3 (Cloudflare R2 — Railway não tem storage de objeto nativo)
- **Frontend**: React + Vite + Recharts (gráficos) ou Vanilla JS (mesmo padrão do HealthReport)
- **Auth**: JWT
- **Hospedagem**: Railway (web + Postgres + Redis no mesmo projeto)
- **Notificações**: WhatsApp/e-mail para lembrete diário e relatório semanal

### 6.2 Provedor de IA: DeepSeek V4 (com camada de abstração)

Decisão confirmada: usar **DeepSeek V4** como motor de IA, pelo custo por token bem mais baixo que alternativas — adequado para um projeto com volume alto de chamadas (classificação de questão por questão, correção de redação, geração de flashcards).

**Ressalva técnica importante**: o modo de visão do DeepSeek V4 é recente e menos testado em produção que alternativas mais maduras, e duas funções centrais do sistema dependem de visão de boa qualidade (ler o caderno de prova e fazer OCR de redação manuscrita). Arquitetura recomendada:

```
app/services/ai_provider/
    base.py            # interface abstrata: classificar_questao(), corrigir_redacao(), 
                        #                     gerar_flashcard(), ocr_imagem()
    deepseek_provider.py   # implementação DeepSeek V4 (texto + visão)
    fallback_ocr.py        # Tesseract ou provedor de visão alternativo, usado só se
                        #                     a qualidade do OCR do DeepSeek não for suficiente
```
Isso evita lock-in: se o modo visão do V4 não performar bem em produção (letra manuscrita, fotos tortas), troca-se só o `ocr_imagem()` sem tocar no resto do sistema. Recomendo um **piloto de validação** logo no início do desenvolvimento: rodar ~20 imagens reais (caderno de prova + redação manuscrita) pelo DeepSeek V4 Vision e comparar a qualidade da transcrição antes de destravar esse módulo em produção.

### 6.3 Modelagem de dados (núcleo)

```sql
-- Matriz de referência (populada 1x a partir do matriz_estruturada.json)
CREATE TABLE area (id SERIAL PRIMARY KEY, nome VARCHAR, peso_medicina NUMERIC DEFAULT 1.0);
CREATE TABLE competencia (id SERIAL PRIMARY KEY, area_id INT REFERENCES area(id), numero INT, descricao TEXT);
CREATE TABLE habilidade (id SERIAL PRIMARY KEY, competencia_id INT REFERENCES competencia(id), codigo VARCHAR, descricao TEXT);

CREATE TABLE aluno (
    id SERIAL PRIMARY KEY, nome VARCHAR, email VARCHAR UNIQUE, senha_hash VARCHAR,
    data_prova_dia1 DATE DEFAULT '2026-11-08',
    data_prova_dia2 DATE DEFAULT '2026-11-15',
    meta_instituicao VARCHAR,
    criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE simulado_upload (
    id SERIAL PRIMARY KEY, aluno_id INT REFERENCES aluno(id),
    arquivo_path VARCHAR, tipo VARCHAR,        -- 'caderno_prova', 'gabarito_oficial'
    total_questoes_detectado INT,
    alternativas_por_questao INT,
    processado BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE questao_identificada (
    id SERIAL PRIMARY KEY,
    simulado_upload_id INT REFERENCES simulado_upload(id),
    numero_questao INT,
    habilidade_id INT REFERENCES habilidade(id),
    tema_livre VARCHAR,
    dificuldade_estimada NUMERIC,
    resposta_aluno VARCHAR(1),
    resposta_correta VARCHAR(1),
    acerto BOOLEAN,
    classificacao_confirmada_manualmente BOOLEAN DEFAULT FALSE
);

CREATE TABLE dominio_habilidade (
    aluno_id INT REFERENCES aluno(id), habilidade_id INT REFERENCES habilidade(id),
    taxa_acerto NUMERIC, ultima_pratica TIMESTAMP, prioridade_calculada NUMERIC,
    PRIMARY KEY (aluno_id, habilidade_id)
);

CREATE TABLE redacao (
    id SERIAL PRIMARY KEY, aluno_id INT REFERENCES aluno(id),
    arquivo_path VARCHAR, texto_ocr TEXT,
    nota_c1 INT, nota_c2 INT, nota_c3 INT, nota_c4 INT, nota_c5 INT, nota_total INT,
    feedback TEXT, criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE flashcard (
    id SERIAL PRIMARY KEY, aluno_id INT REFERENCES aluno(id), habilidade_id INT REFERENCES habilidade(id),
    pergunta TEXT, resposta TEXT,
    fator_facilidade NUMERIC DEFAULT 2.5, intervalo_dias INT DEFAULT 1,
    proxima_revisao DATE, criado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE plano_temporal (
    aluno_id INT REFERENCES aluno(id) PRIMARY KEY,
    semanas_f1 INT, semanas_f2 INT, semanas_f3 INT, semanas_f4 INT,
    carga_diaria_questoes INT, recalculado_em TIMESTAMP DEFAULT now()
);

CREATE TABLE registro_bem_estar (
    aluno_id INT REFERENCES aluno(id), data DATE,
    sono VARCHAR, energia VARCHAR,
    PRIMARY KEY (aluno_id, data)
);
```

### 6.4 Módulos do sistema

1. Auth & perfil
2. Ingestão de simulado (upload → detecção de estrutura → tela de gabarito → classificação → cruzamento)
3. Motor de priorização + planejamento temporal (jobs assíncronos)
4. Redação (upload → OCR → correção)
5. Flashcards e revisão inteligente (geração sob demanda + repetição espaçada)
6. Dashboard/analytics
7. Notificações (lembrete diário, relatório semanal)

### 6.5 Roadmap de construção

| Sprint | Entregável |
|---|---|
| 1 | Banco de dados + seed da matriz (`matriz_estruturada.json`) + auth |
| 2 | Piloto de validação do DeepSeek V4 Vision (OCR de prova e redação reais) — **gate de decisão antes de seguir** |
| 3 | Upload de simulado → detecção de estrutura → tela de gabarito virtual |
| 4 | Classificação de questões por IA + cruzamento de acertos/erros |
| 5 | Motor de priorização + planejamento temporal dinâmico |
| 6 | Dashboard v1 (heatmap, evolução, gráficos) |
| 7 | Módulo de redação completo |
| 8 | Flashcards/revisão inteligente + notificações |

### 6.6 Deploy no Railway
- 3 serviços: `web` (FastAPI), `postgres`, `redis`
- Alembic como release command antes do boot
- Enums como `VARCHAR` + `CHECK constraint` (evita a dor de migration enfrentada no HealthReport)
- Bucket externo (Cloudflare R2) para as imagens de upload

---

## 7. Pendências / decisões em aberto

1. **Piloto de qualidade do DeepSeek V4 Vision** — recomendo rodar antes do Sprint 3, com imagens reais de prova e de redação manuscrita, para confirmar se o OCR é bom o suficiente ou se entra o fallback
2. Confirmar canal de notificação preferido (WhatsApp vs. e-mail) para os lembretes diários/relatório semanal
3. Seguir para o scaffold real do backend (models + rotas) ou protótipo visual da tela de upload/gabarito primeiro?
