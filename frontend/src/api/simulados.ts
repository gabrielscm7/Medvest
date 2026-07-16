import { api } from './client';

export interface SimuladoUpload {
  id: number;
  tipo: string;
  total_questoes_detectado: number | null;
  alternativas_por_questao: number | null;
  processado: boolean;
  criado_em: string;
}

export interface QuestaoGabarito {
  numero_questao: number;
  resposta_aluno: string | null;
  resposta_correta: string | null;
}

export interface Deteccao {
  total_questoes: number;
  alternativas_por_questao: number;
  numeracao_inicial: number;
  questoes: QuestaoGabarito[];
}

export interface QuestaoIdentificada {
  id: number;
  numero_questao: number;
  habilidade_codigo: string | null;
  tema_livre: string | null;
  dificuldade_estimada: number | null;
  texto_questao: string | null;
  resposta_aluno: string | null;
  resposta_correta: string | null;
  acerto: boolean | null;
  classificacao_confirmada_manualmente: boolean;
}

export interface SimuladoCompleto {
  id: number;
  tipo: string;
  total_questoes_detectado: number | null;
  criado_em: string;
  questoes: QuestaoIdentificada[];
}

export function listarSimulados() {
  return api.get<SimuladoUpload[]>('/simulados/');
}

export function uploadSimulado(file: File) {
  return api.upload<SimuladoUpload>('/simulados/upload', file);
}

export function detectarEstrutura(simuladoId: number) {
  return api.post<Deteccao>(`/simulados/${simuladoId}/detectar`);
}

export function preencherGabarito(simuladoId: number, questoes: QuestaoGabarito[]) {
  return api.put<SimuladoCompleto>(`/simulados/${simuladoId}/gabarito`, { questoes });
}

export function obterSimulado(simuladoId: number) {
  return api.get<SimuladoCompleto>(`/simulados/${simuladoId}`);
}

export interface ClassificacaoResponse {
  questoes: QuestaoIdentificada[];
}

export function extrairTextoQuestoes(simuladoId: number) {
  return api.post<ClassificacaoResponse>(`/simulados/${simuladoId}/extrair-texto`);
}

export function classificarQuestoes(simuladoId: number) {
  return api.post<ClassificacaoResponse>(`/simulados/${simuladoId}/classificar`);
}

export function listarHabilidades() {
  return api.get<{ id: number; codigo: string; descricao: string }[]>('/simulados/habilidades');
}

export function deletarSimulado(simuladoId: number) {
  return api.del<{ message: string }>(`/simulados/${simuladoId}`);
}
