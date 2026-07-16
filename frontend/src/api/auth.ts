import { api } from './client';

export interface Aluno {
  id: number;
  nome: string;
  email: string;
  data_prova_dia1: string;
  data_prova_dia2: string;
  meta_instituicao: string | null;
  criado_em: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function register(data: { nome: string; email: string; senha: string; meta_instituicao?: string }) {
  return api.post<Aluno>('/auth/register', data);
}

export function login(data: { email: string; senha: string }) {
  return api.post<TokenResponse>('/auth/login', data);
}

export function me() {
  return api.get<Aluno>('/auth/me');
}

export function bemEstar(data: { data: string; sono: string; energia: string }) {
  return api.post<{ sono: string; energia: string }>('/auth/bem-estar', data);
}
