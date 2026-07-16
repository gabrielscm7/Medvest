import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { obterSimulado, detectarEstrutura, preencherGabarito, type Deteccao, type QuestaoGabarito } from '../api/simulados';

export default function SimuladoDetalhe() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detect, setDetect] = useState<Deteccao | null>(null);
  const [gabarito, setGabarito] = useState<QuestaoGabarito[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const simuladoId = Number(id);

  useEffect(() => {
    obterSimulado(simuladoId).then((s) => {
      if (s.questoes.length > 0) {
        setGabarito(s.questoes.map((q) => ({ numero_questao: q.numero_questao, resposta_aluno: q.resposta_aluno, resposta_correta: q.resposta_correta })));
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
  const letras = alternativas === 5 ? ['A','B','C','D','E'] : ['A','B','C','D'];

  function setResposta(numero: number, campo: 'resposta_aluno' | 'resposta_correta', valor: string) {
    setGabarito((prev) => {
      const existente = prev.find((q) => q.numero_questao === numero);
      if (existente) {
        return prev.map((q) => q.numero_questao === numero ? { ...q, [campo]: valor } : q);
      }
      return [...prev, { numero_questao: numero, [campo]: valor, resposta_aluno: null, resposta_correta: null }];
    });
  }

  async function handleSave() {
    setSaving(true);
    try {
      await preencherGabarito(simuladoId, gabarito);
      navigate('/simulados');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-emerald-600" /></div>;

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/simulados')} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
        <ArrowLeft className="w-4 h-4" /> Voltar
      </button>
      <h1 className="text-2xl font-bold text-gray-800">Simulado #{simuladoId}</h1>
      <p className="text-sm text-gray-500">{total} questões detectadas, {alternativas} alternativas cada</p>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="divide-y divide-gray-100">
          {Array.from({ length: total }, (_, i) => {
            const n = (detect?.numeracao_inicial || 1) + i;
            const q = gabarito.find((g) => g.numero_questao === n);
            return (
              <div key={n} className="p-4 flex items-center gap-4">
                <span className="text-sm font-medium text-gray-600 w-8">#{n}</span>
                <div className="flex-1">
                  <label className="text-xs text-gray-500 block mb-1">Sua resposta</label>
                  <div className="flex gap-1">
                    {letras.map((l) => (
                      <button key={l} onClick={() => setResposta(n, 'resposta_aluno', l)}
                        className={`w-8 h-8 text-xs rounded border transition-colors ${q?.resposta_aluno === l ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-300 hover:border-emerald-400'}`}>
                        {l}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-500 block mb-1">Gabarito</label>
                  <div className="flex gap-1">
                    {letras.map((l) => (
                      <button key={l} onClick={() => setResposta(n, 'resposta_correta', l)}
                        className={`w-8 h-8 text-xs rounded border transition-colors ${q?.resposta_correta === l ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'}`}>
                        {l}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving}
          className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors">
          {saving ? 'Salvando...' : 'Salvar Gabarito'}
        </button>
      </div>
    </div>
  );
}
