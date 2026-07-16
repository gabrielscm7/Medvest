import { api } from './client';

export interface Flashcard {
  id: number;
  habilidade_id: number;
  habilidade_codigo: string | null;
  pergunta: string;
  resposta: string;
  fator_facilidade: number;
  intervalo_dias: number;
  proxima_revisao: string | null;
}

export function pendentes() {
  return api.get<Flashcard[]>('/flashcards/pendentes');
}

export function gerar(habilidade_id: number, quantidade = 3) {
  return api.post<Flashcard[]>('/flashcards/gerar', { habilidade_id, quantidade });
}

export function revisar(flashcardId: number, dificuldade: string) {
  return api.post<Flashcard>(`/flashcards/${flashcardId}/revisar`, { dificuldade });
}
