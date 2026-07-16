# Medvest — Guia de Versão & Especificação (v3)

Este documento serve como guia técnico e de versão para a implementação do sistema Medvest. Ele reflete as diretrizes consolidadas da especificação v3 do projeto.

---

## 1. Visão Geral do Sistema

O **Medvest** é um sistema adaptativo de preparação para o ENEM focado em Medicina. A principal premissa pedagógica é mapear e priorizar o estudo baseado nas **120 habilidades oficiais da matriz de referência do ENEM (INEP)**, em vez de cronogramas genéricos de disciplinas.

### Características Principais (v3):
1. **Sem Banco de Questões Nativo**: Todo o conteúdo avaliativo provém de simulados carregados pelo aluno (imagens/PDF).
2. **Classificação & OCR por IA**: A IA (DeepSeek V4 Vision / Fallbacks) transcreve as provas e as redações, mapeando as questões na matriz oficial de 120 habilidades.
3. **Ficha de Gabarito Virtual**: Grade gerada dinamicamente com base nas questões detectadas na imagem, onde o aluno preenche suas respostas e fornece o gabarito oficial.
4. **Revisão Adaptativa & Flashcards**: Gerados sob demanda por IA nas habilidades identificadas como fracas, usando repetição espaçada (tipo SM-2).
5. **Planejamento Temporal Dinâmico**: Divisão de fases e metas recalculadas automaticamente conforme a data das provas e o nível médio do aluno.

---

## 2. Especificação de Banco de Dados (PostgreSQL / SQLite)

### Tabelas Principais (v3):

1. **area**: Áreas de conhecimento (ex: Ciências da Natureza). Contém `peso_medicina`.
2. **competencia**: Grupo de habilidades dentro de uma área.
3. **habilidade**: As 120 habilidades oficiais do ENEM (H1 a H30 por área).
4. **aluno**: Registro do aluno com metas de curso/instituição e data da prova.
5. **simulado_upload**: Metadados sobre o caderno de questões carregado.
6. **questao_identificada**: Cruzamento de acertos/erros com mapeamento para habilidade e tema livre sugeridos por IA.
7. **dominio_habilidade**: Registro da taxa de acerto por aluno e prioridade recalculada.
8. **redacao**: Registro do texto OCR, notas nas 5 competências do ENEM (C1-C5) e feedback gerado.
9. **flashcard**: Pergunta, resposta e parâmetros de repetição espaçada (SM-2).
10. **plano_temporal**: Fases do macrociclo dinâmico recalculadas.
11. **registro_bem_estar**: Registro diário de sono e energia.

---

## 3. Algoritmo de Priorização

O cálculo de prioridade para a trilha diária é computado sob demanda e ordenado pela fórmula:

$$\text{Prioridade} = \text{peso\_medicina\_area} \times (1 - \text{taxa\_acerto\_recente}) \times \text{fator\_recencia} \times (1 + \text{incidencia\_historica})$$

- **fator_recencia**: Dias desde o último estudo da habilidade / 14 (satura em 2.0).
- **taxa_acerto_recente**: Calculado com base nas tentativas no simulado do aluno para aquela habilidade.

---

## 4. Planejamento Temporal Dinâmico

O macrociclo (divisão em fases F1, F2, F3, F4) e o número diário de questões recomendadas são recalculados em função da data atual e da média de acertos:
- Média < 40%: Foco maior em Fundação (F1) e meta diária de 35 questões.
- Média 40% a 65%: Distribuição balanceada e meta de 25 questões.
- Média > 65%: Foco em Intensificação (F3) e meta de 20 questões.

---

## 5. Roadmap de Construção (Etapas de Implementação)

### Sprint 1: Fundação & Banco de Dados
- Configuração do banco PostgreSQL/SQLite.
- Seed da matriz oficial de 120 habilidades (`matriz_estruturada.json`).
- API básica de registro/login de Alunos (JWT).

### Sprint 2: Validação da IA (Gate de Decisão)
- Piloto de teste do DeepSeek V4 Vision para OCR de provas e redações reais.

### Sprint 3: Upload de Simulado & Gabarito Virtual
- Upload de PDF/imagens.
- Detecção da estrutura e tela interativa de gabarito para inserção de respostas.

### Sprint 4: Classificação Automática & Resultados
- Análise de questões por IA para tageamento automático.
- Processamento e correção do simulado.

### Sprint 5: Motor de Priorização & Planejamento
- Implementação da fórmula de priorização e recálculo dinâmico do macrociclo.

### Sprint 6: Dashboard & Painel Principal
- Visualização do heatmap das 120 habilidades e gráficos de evolução.

### Sprint 7: Módulo de Redação
- OCR de redação manuscrita + rubrica oficial de correção (C1-C5).

### Sprint 8: Flashcards & Notificações
- Flashcards inteligentes e lembretes periódicos.
