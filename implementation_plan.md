# Implementation Plan - Sprint 2: DeepSeek V4 Vision validation pilot

Implement the AI provider abstraction layer, integrate the DeepSeek V4 Vision API via HTTPX, establish a fallback OCR mechanism, and create a runner script to validate OCR accuracy on actual exam/essay images.

## User Review Required

> [!IMPORTANT]
> The DeepSeek V4 API endpoint requires a valid API key (`DEEPSEEK_API_KEY`) and specifies models like `deepseek-v4-pro` or `deepseek-v4-flash`. We will configure the provider to be model-agnostic via env variables.

> [!IMPORTANT]
> Since local test environments might not have Tesseract installed on Windows, the fallback OCR will fall back to a mock handler or standard API fallback to prevent installation blockages.

## Proposed Changes

### AI Service Layer

#### [NEW] [base.py](file:///c:/Users/Mion/OneDrive/Documentos/Projetos%20APP/Medvest/backend/app/services/ai_provider/base.py)
Define the `BaseAIProvider` abstract class with interface methods:
- `ocr_image(self, image_bytes: bytes) -> str`
- `classify_question(self, question_text: str, image_bytes: Optional[bytes] = None) -> dict`
- `correct_essay(self, essay_text: str, image_bytes: Optional[bytes] = None) -> dict`
- `generate_flashcard(self, skill_desc: str) -> dict`

#### [NEW] [deepseek_provider.py](file:///c:/Users/Mion/OneDrive/Documentos/Projetos%20APP/Medvest/backend/app/services/ai_provider/deepseek_provider.py)
Implement `DeepSeekProvider` inheriting from `BaseAIProvider`. It will use `httpx` to send request payloads containing base64-encoded images to the DeepSeek endpoint.

#### [NEW] [fallback_ocr.py](file:///c:/Users/Mion/OneDrive/Documentos/Projetos%20APP/Medvest/backend/app/services/ai_provider/fallback_ocr.py)
Implement a basic fallback/mock OCR helper that can be used when DeepSeek fails or for testing/mocking without a key.

---

### Scripts & Verification

#### [NEW] [run_pilot.py](file:///c:/Users/Mion/OneDrive/Documentos/Projetos%20APP/Medvest/backend/app/scripts/run_pilot.py)
Create a script that:
1. Scans `backend/pilot_images/` for `.png`, `.jpg`, `.jpeg` files.
2. Converts them to base64.
3. Invokes the `DeepSeekProvider`'s `ocr_image` method.
4. Outputs transcripts to terminal and writes logs to `backend/pilot_results.json` for quality analysis.

---

## Verification Plan

### Automated Tests
- Write mock tests for the `DeepSeekProvider` verifying request payload generation.
- Write unit tests for the abstract interface resolution.

### Manual Verification
- Create the directory `backend/pilot_images/`.
- Prompt the user to place test images (exam pages, handwritten essays) in `backend/pilot_images/`.
- Run the command `.venv\Scripts\python -m app.scripts.run_pilot` and check results.
