# Plano 002: Frontend — exibir classificação e permitir confirmação manual

> **Instruções ao executor**: Siga este plano passo a passo. Execute cada
> comando de verificação e confirme o resultado esperado antes de avançar.
> Se algo nas "STOP conditions" ocorrer, PARE e reporte — não improvise.
> Ao finalizar, atualize a linha de status em `plans/README.md`.
>
> **Drift check (execute primeiro)**: `git diff --stat 3446e5f..HEAD -- frontend/src/pages/SimuladoDetalhe.tsx frontend/src/api/simulados.ts`
> Se algum arquivo in-scope mudou desde o SHA do plano, compare os
> trechos de "Current state" com o código atual antes de prosseguir;
> em caso de divergência, trate como STOP condition.

## Status

- **Prioridade**: P1
- **Esforço**: M
- **Risco**: LOW
- **Depende de**: 001
- **Categoria**: direction
- **Planned at**: commit `3446e5f`, 2026-07-16

## Por que isso importa

Depois que o backend classifica as questões por IA (plano 001), o aluno
precisa **ver** a classificação de cada questão (habilidade, dificuldade,
tema) e poder **confirmar ou corrigir** manualmente. Sem essa tela, a
classificação fica invisível e o aluno não confia no resultado.

## Estado atual

- `frontend/src/pages/SimuladoDetalhe.tsx` — Tela de gabarito: mostra
  grade de questões com botões A-E para resposta do aluno e gabarito.
  **Não mostra** nenhuma informação de classificação.
  Fluxo atual: detecta estrutura → mostra grid → salva gabarito → volta.

- `frontend/src/api/simulados.ts:25-43` — `QuestaoIdentificada` type já
  tem os campos `habilidade_codigo`, `tema_livre`, `dificuldade_estimada`,
  `classificacao_confirmada_manualmente`. Precisa adicionar `texto_questao`.

- `frontend/src/api/simulados.ts` — Não tem funções para os novos endpoints
  de extrair-texto e classificar.

**Convenções do repositório — siga estritamente**:
- React 19 com hooks funcionais
- Tailwind CSS 4 para estilização
- lucide-react para ícones
- Tipos na api/*.ts, pages/*.tsx para telas
- Navegação com react-router-dom (`useNavigate`)

## Comandos que você vai precisar

| Propósito | Comando | Esperado |
|-----------|---------|----------|
| Instalar | `cd frontend; npm install` | exit 0 |
| Dev | `cd frontend; npm run dev` | sobe em :5173 |
| Lint | `cd frontend; npx oxlint@latest --fix` | exit 0 |
| Typecheck | `cd frontend; npx tsc --noEmit` | exit 0 |

## Escopo

**In scope**:
- `frontend/src/api/simulados.ts` — tipos e funções para novos endpoints
- `frontend/src/pages/SimuladoDetalhe.tsx` — exibir classificação + botões de ação

**Out of scope**:
- Dashboard, flashcards, redações
- Qualquer alteração no backend
- Estilos ou componentes fora do Tailwind já configurado

## Git workflow

- Branch: `sprint-4-classificacao-front`
- Commits atômicos por passo lógico

## Passos

### Passo 1: Atualizar tipos no client API

Em `frontend/src/api/simulados.ts`:

1.1. Adicionar `texto_questao` em `QuestaoIdentificada`:
```typescript
export interface QuestaoIdentificada {
  id: number;
  numero_questao: number;
  habilidade_codigo: string | null;
  tema_livre: string | null;
  dificuldade_estimada: number | null;
  texto_questao: string | null;  // NOVO
  resposta_aluno: string | null;
  resposta_correta: string | null;
  acerto: boolean | null;
  classificacao_confirmada_manualmente: boolean;
}
```

1.2. Adicionar funções para os novos endpoints:
```typescript
export function extrairTextoQuestoes(simuladoId: number) {
  return api.post<{ questoes: QuestaoIdentificada[] }>(`/simulados/${simuladoId}/extrair-texto`);
}

export function classificarQuestoes(simuladoId: number) {
  return api.post<{ questoes: QuestaoIdentificada[] }>(`/simulados/${simuladoId}/classificar`);
}
```

**Verificar**: `cd frontend; npx tsc --noEmit` → sem erros

### Passo 2: Adicionar botões de ação no SimuladoDetalhe

Em `frontend/src/pages/SimuladoDetalhe.tsx`:

2.1. Importar as novas funções:
```typescript
import { obterSimulado, detectarEstrutura, preencherGabarito, extrairTextoQuestoes, classificarQuestoes, type Deteccao, type QuestaoGabarito, type QuestaoIdentificada } from '../api/simulados';
```

2.2. Adicionar estados:
```typescript
const [classificando, setClassificando] = useState(false);
const [classificacao, setClassificacao] = useState<QuestaoIdentificada[]>([]);
```

2.3. Adicionar funções de ação:
```typescript
async function handleExtrairTexto() {
  setClassificando(true);
  try {
    const resp = await extrairTextoQuestoes(simuladoId);
    setClassificacao(resp.questoes);
  } finally {
    setClassificando(false);
  }
}

async function handleClassificar() {
  setClassificando(true);
  try {
    const resp = await classificarQuestoes(simuladoId);
    setClassificacao(resp.questoes);
    // Recarrega o simulado para atualizar dados
    const s = await obterSimulado(simuladoId);
    if (s.total_questoes_detectado) {
      setDetect({
        total_questoes: s.total_questoes_detectado,
        alternativas_por_questao: 5,
        numeracao_inicial: 1,
        questoes: [],
      });
    }
  } finally {
    setClassificando(false);
  }
}
```

2.4. Renderizar os botões entre o cabeçalho e a grade:
```tsx
<div className="flex gap-3">
  <button onClick={handleExtrairTexto} disabled={classificando}
    className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors text-sm">
    {classificando ? 'Processando...' : 'Extrair Texto'}
  </button>
  <button onClick={handleClassificar} disabled={classificando}
    className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors text-sm">
    {classificando ? 'Classificando...' : 'Classificar por IA'}
  </button>
</div>
```

**Verificar**: `cd frontend; npx tsc --noEmit` → sem erros

### Passo 3: Exibir badge de classificação por questão

Dentro do `.map` de questões, após os botões de gabarito, adicionar:

```tsx
{/* Classificação por IA */}
<div className="w-48">
  {classificacao.length > 0 && (() => {
    const c = classificacao.find(c => c.numero_questao === n);
    if (!c?.habilidade_codigo) return (
      <span className="text-xs text-gray-400 italic">Não classificado</span>
    );
    return (
      <div className="space-y-0.5">
        <span className="inline-block px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-mono">
          {c.habilidade_codigo}
        </span>
        {c.tema_livre && (
          <span className="block text-xs text-gray-500 truncate max-w-[180px]" title={c.tema_livre}>
            {c.tema_livre}
          </span>
        )}
        {c.dificuldade_estimada && (
          <span className={`text-xs ${c.dificuldade_estimada >= 3 ? 'text-red-500' : c.dificuldade_estimada >= 2 ? 'text-amber-500' : 'text-green-500'}`}>
            {['', 'Fácil', 'Média', 'Difícil'][Math.round(c.dificuldade_estimada)] || ''}
          </span>
        )}
      </div>
    );
  })()}
</div>
```

**Verificar**: Recarregue a página em `/simulados/{id}` → deve mostrar botões
"Extrair Texto" e "Classificar por IA". Após classificar, cada questão deve
exibir badge com habilidade, tema e dificuldade.

### Passo 4: Modal de confirmação manual da classificação

Quando o aluno clica no badge de habilidade, abre um popup/modal simples
para confirmar ou alterar a classificação.

4.1. State para controlar:
```typescript
const [editandoClassificacao, setEditandoClassificacao] = useState<number | null>(null); // numero_questao
const [habilidadesList, setHabilidadesList] = useState<{codigo: string; descricao: string}[]>([]);
```

4.2. Carregar lista de habilidades (buscar de um endpoint simples ou ter
uma lista estática — para MVP, use uma lista fixa das 4 áreas principais
com H1 associado como fallback).

Na prática, o ideal é ter um endpoint que retorne as habilidades. Mas para
MVP, vamos apenas permitir confirmar a classificação atual ou marcá-la como
"confirmada manualmente".

Adicione ao final do JSX, antes do botão "Salvar Gabarito":

```tsx
{/* Modal simplificado de confirmação */}
{editandoClassificacao !== null && (
  <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setEditandoClassificacao(null)}>
    <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-xl" onClick={e => e.stopPropagation()}>
      <h3 className="font-semibold text-gray-800 mb-4">Questão #{editandoClassificacao}</h3>
      <p className="text-sm text-gray-600 mb-4">
        A classificação foi atribuída por IA. Para aceitá-la, clique em
        "Confirmar". Para alterar, selecione a habilidade correta.
      </p>
      <div className="flex justify-end gap-3 mt-6">
        <button onClick={() => setEditandoClassificacao(null)}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors text-sm">
          Cancelar
        </button>
        <button onClick={async () => {
          // TODO: chamar endpoint PUT para confirmar classificação
          setEditandoClassificacao(null);
        }}
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm">
          Confirmar Classificação
        </button>
      </div>
    </div>
  </div>
)}
```

**Nota**: O endpoint `PUT` para confirmar classificação manualmente será
implementado como parte do plano 001 (back). A função no frontend deve
ser `api.put<QuestaoIdentificada>(`/simulados/{simuladoId}/questoes/${questaoId}/confirmar-classificacao`, {})`.

**Verificar**: Clique no badge de habilidade de uma questão → modal abre.
Clique "Confirmar Classificação" → modal fecha sem erro.

## Plano de teste

Teste manual:
1. Faça upload de um simulado
2. Clique "Extrair Texto" → aguarde processamento
3. Clique "Classificar por IA" → badges aparecem por questão
4. Clique em um badge → modal de confirmação abre
5. Confirme → modal fecha

## Done criteria

- [ ] Botões "Extrair Texto" e "Classificar por IA" visíveis no SimuladoDetalhe
- [ ] Após classificar, cada questão exibe habilidade, tema e dificuldade
- [ ] Clique no badge abre modal de confirmação
- [ ] `cd frontend; npx tsc --noEmit` sem erros
- [ ] `cd frontend; npx oxlint@latest --fix` sem erros
- [ ] `plans/README.md` atualizado

## STOP conditions

Pare e reporte se:
- Os tipos `QuestaoIdentificada` no frontend não tiverem os campos esperados
  (podem não ter sido atualizados pelo plano 001 ainda)
- O lint ou typecheck falhar por erro não relacionado às mudanças

## Notas de manutenção

- A lista de habilidades no modal de confirmação é um placeholder.
  Futuramente, deve ser substituída por um searchable dropdown que
  busca do backend `/api/habilidades`.
- O modal usa `fixed inset-0` — funciona mas para uma versão polish,
  usar um componente de dialog dedicado.
