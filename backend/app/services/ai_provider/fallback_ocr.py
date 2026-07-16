import re
from typing import Optional
from app.services.ai_provider.base import BaseAIProvider


class FallbackOCRProvider(BaseAIProvider):
    """Fallback provider for offline testing — no API key required."""

    async def ocr_image(self, image_bytes: bytes) -> str:
        return (
            "01. Um estudante precisa calcular a área de um triângulo retângulo "
            "com base 10 cm e altura 5 cm. Qual é a área?\n"
            "02. Leia o texto abaixo e identifique a figura de linguagem "
            "predominante: 'O sol beijava as flores do campo.'\n"
            "03. Sobre a Revolução Francesa, assinale a alternativa correta "
            "acerca da queda da Bastilha.\n"
            "04. Em uma reação química, 2g de hidrogênio reagem com 16g de "
            "oxigênio. Qual a massa de água formada?"
        )

    async def classify_question(
        self, question_text: str, image_bytes: Optional[bytes] = None
    ) -> dict:
        text = question_text.lower()
        if any(w in text for w in ["cálculo", "número", "equação", "gráfico", "função", "área", "volume", "probabilidade"]):
            return {"area": "Matemática e suas Tecnologias", "competencia": 2, "habilidade": "H9", "tema_livre": "matemática básica", "dificuldade": "media"}
        if any(w in text for w in ["reação", "química", "átomo", "molécula", "elemento", "hidrogênio", "oxigênio"]):
            return {"area": "Ciências da Natureza e suas Tecnologias", "competencia": 5, "habilidade": "H17", "tema_livre": "química geral", "dificuldade": "media"}
        if any(w in text for w in ["célula", "dna", "gene", "organismo", "espécie", "ecossistema"]):
            return {"area": "Ciências da Natureza e suas Tecnologias", "competencia": 4, "habilidade": "H14", "tema_livre": "biologia", "dificuldade": "media"}
        if any(w in text for w in ["história", "revolução", "guerra", "política", "sociedade", "bastilha", "economia"]):
            return {"area": "Ciências Humanas e suas Tecnologias", "competencia": 6, "habilidade": "H21", "tema_livre": "história geral", "dificuldade": "media"}
        if any(w in text for w in ["geografia", "mapa", "clima", "relevo", "população", "urbano"]):
            return {"area": "Ciências Humanas e suas Tecnologias", "competencia": 7, "habilidade": "H24", "tema_livre": "geografia", "dificuldade": "media"}
        if any(w in text for w in ["grafia", "leitura", "texto", "língua", "linguagem", "figura", "literatura"]):
            return {"area": "Linguagens, Códigos e suas Tecnologias", "competencia": 1, "habilidade": "H3", "tema_livre": "interpretação textual", "dificuldade": "media"}

        return {"area": "Ciências da Natureza e suas Tecnologias", "competencia": 1, "habilidade": "H1", "tema_livre": "classificação automática (fallback)", "dificuldade": "media"}

    async def correct_essay(
        self, essay_text: str, image_bytes: Optional[bytes] = None
    ) -> dict:
        words = len(essay_text.split())
        base = min(160, int(words * 0.5))
        return {
            "nota_c1": base,
            "nota_c2": base,
            "nota_c3": base,
            "nota_c4": base,
            "nota_c5": base,
            "nota_total": base * 5,
            "feedback": "[FALLBACK] Correção simulada. Use o DeepSeek para correção real.",
        }

    async def generate_flashcard(
        self, habilidade_desc: str, nivel: str = "medio"
    ) -> dict:
        return {
            "pergunta": f"Explique o conceito relacionado a: {habilidade_desc[:80]}",
            "resposta": "Revise o conteúdo programático desta habilidade na matriz do ENEM.",
        }

    async def detect_exam_structure(self, image_bytes: bytes) -> dict:
        return {"total_questoes": 45, "alternativas_por_questao": 5, "numeracao_inicial": 1}


_FALLBACK_QUESTIONS = [
    {"numero": 1, "texto": "Um estudante precisa calcular a área de um triângulo retângulo com base 10 cm e altura 5 cm. Qual é a área?"},
    {"numero": 2, "texto": "Leia o texto abaixo e identifique a figura de linguagem predominante: 'O sol beijava as flores do campo.'"},
    {"numero": 3, "texto": "Sobre a Revolução Francesa, assinale a alternativa correta acerca da queda da Bastilha."},
    {"numero": 4, "texto": "Em uma reação química, 2g de hidrogênio reagem com 16g de oxigênio. Qual a massa de água formada?"},
    {"numero": 5, "texto": "Qual a função sintática do termo destacado em 'Os alunos estudam para a prova'?"},
]


def get_fallback_provider() -> FallbackOCRProvider:
    return FallbackOCRProvider()
