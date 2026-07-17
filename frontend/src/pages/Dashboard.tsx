import { useEffect, useState } from 'react';
import { BookOpen, FileText, Brain, Target, TrendingUp, Calendar } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { getDashboard, type Dashboard } from '../api/dashboard';

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" /></div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Target, label: 'Nota Estimada', value: `${data?.nota_estimada ?? 0}%`, color: 'text-emerald-600' },
          { icon: TrendingUp, label: 'Taxa de Acerto', value: `${data?.taxa_acerto_geral ?? 0}%`, color: 'text-blue-600' },
          { icon: BookOpen, label: 'Simulados', value: String(data?.total_simulados ?? 0), color: 'text-violet-600' },
          { icon: FileText, label: 'Redações', value: String(data?.total_redacoes ?? 0), color: 'text-orange-600' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
              </div>
              <Icon className={`w-10 h-10 ${color} opacity-20`} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-600" />
            Plano Temporal
          </h2>
          {data?.plano_temporal ? (
            <div className="space-y-3">
              {[
                { fase: 'F1 — Fundação', semanas: data.plano_temporal.semanas_f1, color: 'bg-red-400' },
                { fase: 'F2 — Consolidação', semanas: data.plano_temporal.semanas_f2, color: 'bg-yellow-400' },
                { fase: 'F3 — Intensificação', semanas: data.plano_temporal.semanas_f3, color: 'bg-emerald-400' },
                { fase: 'F4 — Polimento', semanas: data.plano_temporal.semanas_f4, color: 'bg-blue-400' },
              ].map(({ fase, semanas, color }) => {
                const total = data.plano_temporal!.semanas_f1 + data.plano_temporal!.semanas_f2 +
                  data.plano_temporal!.semanas_f3 + data.plano_temporal!.semanas_f4;
                return (
                  <div key={fase}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{fase}</span>
                      <span className="text-gray-500">{semanas} semanas</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${(semanas / total) * 100}%` }} />
                    </div>
                  </div>
                );
              })}
              <p className="text-sm text-gray-500 mt-3">Carga diária recomendada: <strong>{data.plano_temporal.carga_diaria_questoes}</strong> questões</p>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Nenhum plano gerado ainda.</p>
          )}
        </div>

        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Brain className="w-4 h-4 text-emerald-600" />
            Habilidades Prioritárias
          </h2>
          {data?.heatmap && data.heatmap.length > 0 ? (
            <div className="space-y-2">
              {data.heatmap.slice(0, 8).map((h) => (
                <div key={h.codigo} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono">{h.codigo}</span>
                    <span className="text-gray-600 truncate max-w-[200px]">{h.descricao}</span>
                  </div>
                  <span className="text-xs font-medium" style={{ color: h.taxa_acerto < 0.4 ? '#dc2626' : h.taxa_acerto < 0.65 ? '#d97706' : '#16a34a' }}>
                    {Math.round(h.taxa_acerto * 100)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Complete um simulado para gerar análise.</p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
        <h2 className="font-semibold text-gray-800 mb-4">Questões Respondidas</h2>
        <div className="flex items-end gap-2">
          <p className="text-4xl font-bold text-emerald-600">{data?.questoes_respondidas ?? 0}</p>
          <p className="text-gray-500 mb-1">questões no total</p>
        </div>
      </div>

      {data?.graficos_area && data.graficos_area.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Taxa de Acerto por Área</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.graficos_area}>
              <XAxis dataKey="nome" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip formatter={(v: any) => `${Math.round(Number(v) * 100)}%`} />
              <Bar dataKey="taxa_acerto" fill="#059669" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

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
                label={({ payload }) => `${(payload as any).tema} (${((payload as any).percent * 100).toFixed(0)}%)`}
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

      {data?.graficos_competencia && data.graficos_competencia.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Competências (Top 10)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.graficos_competencia.slice(0, 10)} layout="vertical">
              <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${Math.round(Number(v) * 100)}%`} />
              <YAxis type="category" dataKey="descricao" width={200} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: any) => `${Math.round(Number(v) * 100)}%`} />
              <Bar dataKey="taxa_acerto" fill="#2563eb" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
