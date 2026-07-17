import { api } from './client';

export interface HabilidadeHeatmap {
  codigo: string;
  descricao: string;
  taxa_acerto: number;
  prioridade: number;
  ultima_pratica: string | null;
}

export interface PlanoTemporal {
  semanas_f1: number;
  semanas_f2: number;
  semanas_f3: number;
  semanas_f4: number;
  carga_diaria_questoes: number;
}

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

export interface Dashboard {
  nota_estimada: number;
  nota_corte: number;
  total_simulados: number;
  total_redacoes: number;
  questoes_respondidas: number;
  taxa_acerto_geral: number;
  heatmap: HabilidadeHeatmap[];
  plano_temporal: PlanoTemporal | null;
  graficos_area: AreaChartData[];
  graficos_competencia: CompetenciaChartData[];
  graficos_tema: TemaChartData[];
}

export function getDashboard() {
  return api.get<Dashboard>('/dashboard/');
}
