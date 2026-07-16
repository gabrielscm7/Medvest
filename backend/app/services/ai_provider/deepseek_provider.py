import base64
import json
from typing import Optional

import httpx

from app.core.config import settings
from app.services.ai_provider.base import BaseAIProvider

SYSTEM_PROMPT = (
    "Você é um assistente especializado em educação para o ENEM, focado em Medicina. "
    "Responda sempre em português brasileiro, com precisão técnica. "
    "Seu papel é auxiliar na classificação de questões, correção de redações "
    "e geração de flashcards baseados na matriz de referência oficial do INEP."
)


class DeepSeekProvider(BaseAIProvider):

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model or "deepseek-v4-pro"
        self.base_url = "https://api.deepseek.com/v1"
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if not hasattr(self, "_http_client") or self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120),
            )
        return self._http_client

    async def _call(self, messages: list[dict], max_tokens: int = 2048) -> str:
        client = self._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def ocr_image(self, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Transcreva TODO o texto visível nesta imagem de prova ENEM. "
                            "Se for redação manuscrita, transcreva fielmente. "
                            "Retorne JSON: {\"texto\": \"...\"}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ]
        result = await self._call(messages, max_tokens=4096)
        return json.loads(result).get("texto", "")

    async def classify_question(
        self, question_text: str, image_bytes: Optional[bytes] = None
    ) -> dict:
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"Classifique esta questão do ENEM conforme a matriz de referência. "
                    f"Retorne JSON: {{\"area\": \"...\", \"competencia\": N, \"habilidade\": \"H...\", "
                    f"\"tema_livre\": \"...\", \"dificuldade\": \"facil|media|dificil\"}}\n\n"
                    f"Questão:\n{question_text}"
                ),
            }
        ]
        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode()
            content.insert(
                0,
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        result = await self._call(messages)
        return json.loads(result)

    async def correct_essay(
        self, essay_text: str, image_bytes: Optional[bytes] = None
    ) -> dict:
        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "Corrija esta redação estilo ENEM usando a rubrica oficial das 5 competências "
                    "(C1 a C5, cada uma de 0 a 200). Avalie:\n"
                    "C1: Domínio da norma culta\n"
                    "C2: Compreensão do tema e estrutura dissertativa\n"
                    "C3: Argumentação e seleção de informações\n"
                    "C4: Coesão textual\n"
                    "C5: Proposta de intervenção\n\n"
                    "Retorne JSON: {\"nota_c1\": N, \"nota_c2\": N, \"nota_c3\": N, "
                    "\"nota_c4\": N, \"nota_c5\": N, \"nota_total\": N, "
                    "\"feedback\": \"...\"}\n\n"
                    f"Redação:\n{essay_text}"
                ),
            }
        ]
        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode()
            content.insert(
                0,
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        result = await self._call(messages, max_tokens=4096)
        return json.loads(result)

    async def generate_flashcard(
        self, habilidade_desc: str, nivel: str = "medio"
    ) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Gere um flashcard no estilo pergunta/resposta para estudar a seguinte "
                    f"habilidade do ENEM, com dificuldade nível {nivel}:\n\n"
                    f"{habilidade_desc}\n\n"
                    f"Retorne JSON: {{\"pergunta\": \"...\", \"resposta\": \"...\"}}"
                ),
            },
        ]
        result = await self._call(messages)
        return json.loads(result)

    async def detect_exam_structure(self, image_bytes: bytes) -> dict:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analise esta imagem de prova/caderno de questões do ENEM e detecte:\n"
                            "- Quantidade total de questões\n"
                            "- Número de alternativas por questão (4 ou 5)\n"
                            "- Numeração inicial\n"
                            "Retorne JSON: {\"total_questoes\": N, \"alternativas_por_questao\": N, "
                            "\"numeracao_inicial\": N}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ]
        result = await self._call(messages)
        return json.loads(result)


def get_ai_provider() -> DeepSeekProvider:
    return DeepSeekProvider()
