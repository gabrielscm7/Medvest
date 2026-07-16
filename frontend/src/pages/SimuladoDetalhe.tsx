import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Sparkles, FileText, CheckCircle, Trash2 } from 'lucide-react';
import {
  obterSimulado, detectarEstrutura, preencherGabarito,
  extrairTextoQuestoes, classificarQuestoes, deletarSimulado,
  type Deteccao, type QuestaoGabarito, type QuestaoIdentificada
} from '../api/simulados';

export default function SimuladoDetalhe() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detect, setDetect] = useState<Deteccao | null>(null);
  const [gabarito, setGabarito] = useState<QuestaoGabarito[]>([]);
  const [classificacao, setClassificacao] = useState<QuestaoIdentificada[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [editandoClassificacao, setEditandoClassificacao] = useState<number | null>(null);
  const simuladoId = Number(id);

  useEffect(() => {
    obterSimulado(simuladoId).then((s) => {
      if (s.questoes.length > 0) {
        setGabarito(
          s.questoes.map((q) => ({
            numero_questao: q.numero_questao,
            resposta_aluno: q.resposta_aluno,
            resposta_correta: q.resposta_correta,
          }))
        );
        setClassificacao(s.questoes);
      }
      if (s.total_questoes_detectado) {
        setDetect({
          total_questoes: s.total_questoes_detectado,
          alternativas_por_questao: 5,
          numeracao_inicial: 1,
          questoes: [],
        });
        setLoading(false);
      } else {
        detectarEstrutura(simuladoId).then(setDetect).finally(() => setLoading(false));
      }
    }).catch(() => setLoading(false));
  }, [simuladoId]);

  const questoes = detect?.questoes || gabarito;
  const total = detect?.total_questoes || questoes.length || 45;
  const alternativas = detect?.alternativas_por_questao || 5;
  const letras = alternativas === 5 ? ['A', 'B', 'C', 'D', 'E'] : ['A', 'B', 'C', 'D'];

  function setResposta(numero: number, campo: 'resposta_aluno' | 'resposta_correta', valor: string) {
    setGabarito((prev) => {
      const existente = prev.find((q) => q.numero_questao === numero);
      if (existente) {
        return prev.map((q) =>
          q.numero_questao === numero ? { ...q, [campo]: valor } : q
        );
      }
      return [...prev, { numero_questao: numero, resposta_aluno: null, resposta_correta: null, [campo]: valor }];
    });
  }

  async function handleSave() {
    setProcessing(true);
    try {
      await preencherGabarito(simuladoId, gabarito);
      navigate('/simulados');
    } finally {
      setProcessing(false);
    }
  }

  async function handleExtrairTexto() {
    setProcessing(true);
    try {
      const resp = await extrairTextoQuestoes(simuladoId);
      setClassificacao((prev) => {
        const map = new Map(prev.map((q) => [q.numero_questao, q]));
        for (const q of resp.questoes) map.set(q.numero_questao, q);
        return [...map.values()];
      });
    } finally {
      setProcessing(false);
    }
  }

  async function handleDeletar() {
    if (!confirm('Tem certeza que deseja excluir este simulado?')) return;
    await deletarSimulado(simuladoId);
    navigate('/simulados');
  }

  async function handleClassificar() {
    setProcessing(true);
    try {
      const resp = await classificarQuestoes(simuladoId);
      setClassificacao((prev) => {
        const map = new Map(prev.map((q) => [q.numero_questao, q]));
        for (const q of resp.questoes) map.set(q.numero_questao, q);
        return [...map.values()];
      });
    } finally {
      setProcessing(false);
    }
  }

  function getClassificacao(n: number) {
    return classificacao.find((c) => c.numero_questao === n);
  }

  if (loading)
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
      </div>
    );

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/simulados')}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="w-4 h-4" /> Voltar
      </button>

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Simulado #{simuladoId}</h1>
          <p className="text-sm text-gray-500">
            {total} questões detectadas, {alternativas} alternativas cada
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleExtrairTexto}
            disabled={processing}
            className="flex items-center gap-1.5 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 transition-colors text-sm"
          >
            <FileText className="w-4 h-4" />
            {processing ? 'Processando...' : 'Extrair Texto'}
          </button>
          <button
            onClick={handleClassificar}
            disabled={processing}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors text-sm"
          >
            <Sparkles className="w-4 h-4" />
            {processing ? 'Classificando...' : 'Classificar por IA'}
          </button>
          <button
            onClick={handleDeletar}
            disabled={processing}
            className="flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors text-sm"
          >
            <Trash2 className="w-4 h-4" />
            Excluir
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="divide-y divide-gray-100">
          {Array.from({ length: total }, (_, i) => {
            const n = (detect?.numeracao_inicial || 1) + i;
            const q = gabarito.find((g) => g.numero_questao === n);
            const c = getClassificacao(n);
            return (
              <div key={n} className="p-4 flex items-center gap-4">
                <span className="text-sm font-medium text-gray-600 w-8">#{n}</span>

                <div className="flex-1">
                  <label className="text-xs text-gray-500 block mb-1">Sua resposta</label>
                  <div className="flex gap-1">
                    {letras.map((l) => (
                      <button
                        key={l}
                        onClick={() => setResposta(n, 'resposta_aluno', l)}
                        className={`w-8 h-8 text-xs rounded border transition-colors ${
                          q?.resposta_aluno === l
                            ? 'bg-emerald-600 text-white border-emerald-600'
                            : 'bg-white text-gray-600 border-gray-300 hover:border-emerald-400'
                        }`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex-1">
                  <label className="text-xs text-gray-500 block mb-1">Gabarito</label>
                  <div className="flex gap-1">
                    {letras.map((l) => (
                      <button
                        key={l}
                        onClick={() => setResposta(n, 'resposta_correta', l)}
                        className={`w-8 h-8 text-xs rounded border transition-colors ${
                          q?.resposta_correta === l
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                        }`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="w-44 shrink-0">
                  {c?.habilidade_codigo ? (
                    <button
                      onClick={() => setEditandoClassificacao(n)}
                      className="text-left space-y-0.5 group"
                    >
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-mono group-hover:bg-blue-200 transition-colors">
                        {c.habilidade_codigo}
                        {c.classificacao_confirmada_manualmente && (
                          <CheckCircle className="w-3 h-3" />
                        )}
                      </span>
                      {c.tema_livre && (
                        <span
                          className="block text-xs text-gray-500 truncate max-w-[180px]"
                          title={c.tema_livre}
                        >
                          {c.tema_livre}
                        </span>
                      )}
                      {c.dificuldade_estimada && (
                        <span
                          className={`text-xs ${
                            c.dificuldade_estimada >= 3
                              ? 'text-red-500'
                              : c.dificuldade_estimada >= 2
                                ? 'text-amber-500'
                                : 'text-green-500'
                          }`}
                        >
                          {['', 'Fácil', 'Média', 'Difícil'][Math.round(c.dificuldade_estimada)] || ''}
                        </span>
                      )}
                    </button>
                  ) : c?.texto_questao ? (
                    <span className="text-xs text-gray-400 italic">Não classificado</span>
                  ) : (
                    <span className="text-xs text-gray-300 italic">Sem texto</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {editandoClassificacao !== null && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          onClick={() => setEditandoClassificacao(null)}
        >
          <div
            className="bg-white rounded-xl p-6 max-w-md w-full shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-semibold text-gray-800 mb-4">
              Questão #{editandoClassificacao}
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Classificação atual:{' '}
              <strong>{getClassificacao(editandoClassificacao)?.habilidade_codigo || 'N/A'}</strong>
              {getClassificacao(editandoClassificacao)?.tema_livre && (
                <> — {getClassificacao(editandoClassificacao)?.tema_livre}</>
              )}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              A classificação foi atribuída por IA. Para aceitá-la, clique em "Confirmar".
            </p>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setEditandoClassificacao(null);
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors text-sm"
              >
                Fechar
              </button>
              <button
                onClick={() => {
                  setEditandoClassificacao(null);
                }}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm"
              >
                Confirmar Classificação
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={processing}
          className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {processing ? 'Salvando...' : 'Salvar Gabarito'}
        </button>
      </div>
    </div>
  );
}
