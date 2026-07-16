import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Eye, Trash2 } from 'lucide-react';
import { listarSimulados, uploadSimulado, deletarSimulado, type SimuladoUpload } from '../api/simulados';

export default function Simulados() {
  const [lista, setLista] = useState<SimuladoUpload[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletando, setDeletando] = useState<number | null>(null);
  const navigate = useNavigate();

  function carregar() {
    setLoading(true);
    listarSimulados().then(setLista).finally(() => setLoading(false));
  }

  useEffect(() => { carregar(); }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const sim = await uploadSimulado(file);
      navigate(`/simulados/${sim.id}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeletar(id: number) {
    if (!confirm('Tem certeza que deseja excluir este simulado? As questões associadas também serão removidas.')) return;
    setDeletando(id);
    try {
      await deletarSimulado(id);
      setLista((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setDeletando(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Simulados</h1>
        <label className={`flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg cursor-pointer hover:bg-emerald-700 transition-colors ${uploading ? 'opacity-50' : ''}`}>
          <Upload className="w-4 h-4" />
          {uploading ? 'Enviando...' : 'Upload'}
          <input type="file" accept="image/*,application/pdf" onChange={handleUpload} className="hidden" disabled={uploading} />
        </label>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" /></div>
      ) : lista.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nenhum simulado enviado ainda.</p>
          <p className="text-sm">Faça upload de um caderno de provas para começar.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {lista.map((s) => (
            <div key={s.id}
              className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm flex items-center justify-between cursor-pointer hover:shadow-md transition-shadow group">
              <div className="flex-1" onClick={() => navigate(`/simulados/${s.id}`)}>
                <p className="font-medium text-gray-800">
                  Simulado #{s.id}
                  {s.processado && <span className="ml-2 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">Processado</span>}
                </p>
                <p className="text-sm text-gray-500">
                  {s.total_questoes_detectado ? `${s.total_questoes_detectado} questões` : 'Aguardando detecção'} • {new Date(s.criado_em).toLocaleDateString('pt-BR')}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => { e.stopPropagation(); navigate(`/simulados/${s.id}`); }}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Ver simulado"
                >
                  <Eye className="w-5 h-5" />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeletar(s.id); }}
                  disabled={deletando === s.id}
                  className="p-2 text-red-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  title="Excluir simulado"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
