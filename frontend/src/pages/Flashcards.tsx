import { useEffect, useState } from 'react';
import { Sparkles, Loader2, ThumbsUp, Minus, ThumbsDown } from 'lucide-react';
import { pendentes, revisar, type Flashcard } from '../api/flashcards';

export default function FlashcardsPage() {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Flashcard | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    pendentes().then(setCards).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (cards.length > 0 && !selected) {
      setSelected(cards[0]);
    }
  }, [cards, selected]);

  async function handleRevisar(dificuldade: string) {
    if (!selected) return;
    await revisar(selected.id, dificuldade);
    const rest = cards.filter((c) => c.id !== selected.id);
    setCards(rest);
    setSelected(rest.length > 0 ? rest[0] : null);
    setShowAnswer(false);
  }

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-emerald-600" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Flashcards</h1>
        <button onClick={async () => {
          setLoading(true);
          try { const c = await pendentes(); setCards(c); } finally { setLoading(false); }
        }} className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
          Atualizar
        </button>
      </div>

      {selected ? (
        <div className="max-w-lg mx-auto">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 min-h-[200px] flex flex-col items-center justify-center text-center cursor-pointer"
            onClick={() => setShowAnswer(!showAnswer)}>
            <p className="text-xs text-gray-400 mb-2">
              {selected.habilidade_codigo} • Revisão em {selected.intervalo_dias}d
            </p>
            {!showAnswer ? (
              <p className="text-lg font-medium text-gray-800">{selected.pergunta}</p>
            ) : (
              <p className="text-base text-gray-700">{selected.resposta}</p>
            )}
            <p className="text-xs text-gray-400 mt-4">{showAnswer ? 'Clique para ver a pergunta' : 'Clique para ver a resposta'}</p>
          </div>

          {showAnswer && (
            <div className="flex justify-center gap-4 mt-6">
              {[
                { label: 'Fácil', icon: ThumbsUp, value: 'facil', color: 'bg-emerald-600 hover:bg-emerald-700' },
                { label: 'Médio', icon: Minus, value: 'medio', color: 'bg-yellow-500 hover:bg-yellow-600' },
                { label: 'Difícil', icon: ThumbsDown, value: 'dificil', color: 'bg-red-500 hover:bg-red-600' },
              ].map(({ label, icon: Icon, value, color }) => (
                <button key={value} onClick={() => handleRevisar(value)}
                  className={`flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors ${color}`}>
                  <Icon className="w-4 h-4" /> {label}
                </button>
              ))}
            </div>
          )}

          <p className="text-center text-sm text-gray-400 mt-4">{cards.length} flashcards pendentes</p>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nenhum flashcard pendente de revisão.</p>
        </div>
      )}
    </div>
  );
}
