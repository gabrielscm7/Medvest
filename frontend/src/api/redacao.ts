import { api } from './client';

export interface Redacao {
  id: number;
  texto_ocr: string | null;
  nota_c1: number | null;
  nota_c2: number | null;
  nota_c3: number | null;
  nota_c4: number | null;
  nota_c5: number | null;
  nota_total: number | null;
  feedback: string | null;
  criado_em: string;
}

export interface Correcao {
  texto_ocr: string;
  notas: { competencia: string; nota: number; maximo: number }[];
  nota_total: number;
  feedback: string;
}

export function listarRedacoes() {
  return api.get<Redacao[]>('/redacoes/');
}

export function uploadRedacao(file: File) {
  return api.upload<Redacao>('/redacoes/upload', file);
}

export function corrigirRedacao(redacaoId: number) {
  return api.post<Correcao>(`/redacoes/${redacaoId}/corrigir`);
}

export function obterRedacao(redacaoId: number) {
  return api.get<Redacao>(`/redacoes/${redacaoId}`);
}
