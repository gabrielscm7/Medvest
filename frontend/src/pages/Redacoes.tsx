import { useEffect, useState } from 'react';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { listarRedacoes, uploadRedacao, corrigirRedacao, type Redacao, type Correcao } from '../api/redacao';

export default function Redacoes() {
  const [lista, setLista] = useState<Redacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [corrigindo, setCorrigindo] = useState<number | null>(null);
  const [correcao, setCorrecao] = useState<{ redacaoId: number; data: Correcao } | null>(null);

  useEffect(() => {
    listarRedacoes().then(setLista).finally(() => setLoading(false));
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const red = await uploadRedacao(file);
      setLista((prev) => [red, ...prev]);
    } finally {
      setUploading(false);
    }
  }

  async function handleCorrigir(id: number) {
    setCorrigindo(id);
    try {
      const data = await corrigirRedacao(id);
      setCorrecao({ redacaoId: id, data });
    } finally {
      setCorrigindo(null);
    }
  }

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-emerald-600" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Redações</h1>
        <label className={`flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg cursor-pointer hover:bg-emerald-700 transition-colors ${uploading ? 'opacity-50' : ''}`}>
          <Upload className="w-4 h-4" />
          {uploading ? 'Enviando...' : 'Upload'}
          <input type="file" accept="image/*" onChange={handleUpload} className="hidden" disabled={uploading} />
        </label>
      </div>

      {lista.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nenhuma redação enviada.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {lista.map((r) => {
            const show = correcao?.redacaoId === r.id;
            return (
              <div key={r.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">Redação #{r.id}</p>
                    <p className="text-sm text-gray-500">{new Date(r.criado_em).toLocaleDateString('pt-BR')}</p>
                  </div>
                  {r.nota_total !== null ? (
                    <span className="text-lg font-bold text-emerald-600">{r.nota_total}/1000</span>
                  ) : (
                    <button onClick={() => handleCorrigir(r.id)} disabled={corrigindo === r.id}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                      {corrigindo === r.id ? 'Corrigindo...' : 'Corrigir'}
                    </button>
                  )}
                </div>
                {show && correcao && (
                  <div className="border-t px-4 py-3 space-y-3 bg-gray-50">
                    <div className="grid grid-cols-5 gap-2">
                      {correcao.data.notas.map((n) => (
                        <div key={n.competencia} className="text-center bg-white rounded-lg p-2 border">
                          <p className="text-xs text-gray-500">{n.competencia}</p>
                          <p className="text-lg font-bold text-blue-600">{n.nota}</p>
                          <p className="text-xs text-gray-400">/200</p>
                        </div>
                      ))}
                    </div>
                    <div className="bg-white rounded-lg p-3 border">
                      <p className="text-xs font-medium text-gray-500 mb-1">Texto OCR</p>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-3">{correcao.data.texto_ocr}</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 border">
                      <p className="text-xs font-medium text-gray-500 mb-1">Feedback</p>
                      <p className="text-sm text-gray-700">{correcao.data.feedback}</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
