import re
from typing import Optional
from app.services.ai_provider.base import BaseAIProvider


class FallbackOCRProvider(BaseAIProvider):
    """Fallback provider for offline testing — no API key required."""

    async def ocr_image(self, image_bytes: bytes) -> str:
        return "[FALLBACK OCR] Imagem recebida, OCR real requer DeepSeek API."

    async def classify_question(
        self, question_text: str, image_bytes: Optional[bytes] = None
    ) -> dict:
        area = "Ciências da Natureza e suas Tecnologias"
        if any(w in question_text.lower() for w in ["grafia", "leitura", "texto", "língua", "linguagem"]):
            area = "Linguagens, Códigos e suas Tecnologias"
        elif any(w in question_text.lower() for w in ["cálculo", "número", "equação", "gráfico", "função"]):
            area = "Matemática e suas Tecnologias"
        elif any(w in question_text.lower() for w in ["história", "geografia", "sociedade", "política"]):
            area = "Ciências Humanas e suas Tecnologias"

        return {
            "area": area,
            "competencia": 1,
            "habilidade": "H1",
            "tema_livre": "classificação automática (fallback)",
            "dificuldade": "media",
        }

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


def get_fallback_provider() -> FallbackOCRProvider:
    return FallbackOCRProvider()
