import base64
import json
import os
from typing import Optional

import httpx

from app.core.config import settings


class QwenProvider:
    """Qwen2.5-VL provider — exclusively for OCR and vision tasks."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.QWEN_API_KEY
        self.model = model or os.getenv("QWEN_MODEL", "qwen2.5-vl-72b")
        self.base_url = (
            base_url
            or settings.QWEN_BASE_URL
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120),
            )
        return self._client

    async def _call(self, messages: list[dict], max_tokens: int = 4096) -> str:
        client = self._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def ocr_image(self, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Transcreva TODO o texto visível nesta imagem. "
                            "Se for redação manuscrita, transcreva fielmente. "
                            "Se for prova com questões, extraia cada questão com seu texto completo. "
                            "Retorne apenas o texto puro, sem formatação JSON."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ]
        return await self._call(messages)

    async def detect_exam_structure(self, image_bytes: bytes) -> dict:
        b64 = base64.b64encode(image_bytes).decode()
        messages = [
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
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            },
        ]
        result = await self._call(messages)
        return json.loads(result)


def get_qwen_provider() -> QwenProvider:
    return QwenProvider()
