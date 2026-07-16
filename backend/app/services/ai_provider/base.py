from abc import ABC, abstractmethod
from typing import Optional


class BaseAIProvider(ABC):

    @abstractmethod
    async def ocr_image(self, image_bytes: bytes) -> str: ...

    @abstractmethod
    async def classify_question(
        self, question_text: str, image_bytes: Optional[bytes] = None
    ) -> dict: ...

    @abstractmethod
    async def correct_essay(
        self, essay_text: str, image_bytes: Optional[bytes] = None
    ) -> dict: ...

    @abstractmethod
    async def generate_flashcard(self, habilidade_desc: str, nivel: str = "medio") -> dict: ...

    @abstractmethod
    async def detect_exam_structure(self, image_bytes: bytes) -> dict: ...
