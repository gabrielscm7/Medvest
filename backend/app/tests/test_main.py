import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine, Base
from app.main import app
from app.models import Area, Competencia, Habilidade

client = TestClient(app)

ALUNO_EMAIL = "test@medvest.com"
ALUNO_SENHA = "senha123"


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _register():
    return client.post(
        "/api/auth/register",
        json={"nome": "Aluno Teste", "email": ALUNO_EMAIL, "senha": ALUNO_SENHA},
    )


def _login():
    resp = client.post(
        "/api/auth/login", json={"email": ALUNO_EMAIL, "senha": ALUNO_SENHA}
    )
    return resp.json()["access_token"]


def _auth_header(token=None):
    token = token or _login()
    return {"Authorization": f"Bearer {token}"}


def _seed_habilidade() -> int:
    db = SessionLocal()
    area = Area(nome="Matemática e suas Tecnologias", peso_medicina=1.5)
    db.add(area)
    db.commit()
    db.refresh(area)
    comp = Competencia(area_id=area.id, numero=1, descricao="Números")
    db.add(comp)
    db.commit()
    db.refresh(comp)
    hab = Habilidade(
        competencia_id=comp.id, codigo="H1", descricao="Reconhecer números"
    )
    db.add(hab)
    db.commit()
    db.refresh(hab)
    hab_id = hab.id
    db.close()
    return hab_id


class TestAuth:
    def test_register(self):
        resp = _register()
        assert resp.status_code == 201
        assert resp.json()["email"] == ALUNO_EMAIL

    def test_register_duplicate(self):
        _register()
        resp = _register()
        assert resp.status_code == 409

    def test_login(self):
        _register()
        resp = client.post(
            "/api/auth/login", json={"email": ALUNO_EMAIL, "senha": ALUNO_SENHA}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_invalid(self):
        resp = client.post(
            "/api/auth/login", json={"email": ALUNO_EMAIL, "senha": "wrong"}
        )
        assert resp.status_code == 401

    def test_me(self):
        _register()
        token = _login()
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == ALUNO_EMAIL

    def test_me_unauthorized(self):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_bem_estar(self):
        _register()
        token = _login()
        resp = client.post(
            "/api/auth/bem-estar",
            json={"data": "2026-07-16", "sono": "bom", "energia": "alta"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.json()["sono"] == "bom"


class TestSimulados:
    def test_list_empty(self):
        _register()
        token = _login()
        resp = client.get("/api/simulados/", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_upload_and_get(self):
        _register()
        token = _login()
        upload_resp = client.post(
            "/api/simulados/upload",
            files={"file": ("test.png", b"fake_image_bytes", "image/png")},
            headers=_auth_header(token),
        )
        assert upload_resp.status_code == 201
        sim_id = upload_resp.json()["id"]

        resp = client.get(f"/api/simulados/{sim_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == sim_id

    def test_gabarito(self):
        _register()
        token = _login()
        upload_resp = client.post(
            "/api/simulados/upload",
            files={"file": ("test.png", b"fake_image_bytes", "image/png")},
            headers=_auth_header(token),
        )
        sim_id = upload_resp.json()["id"]

        resp = client.put(
            f"/api/simulados/{sim_id}/gabarito",
            json={
                "questoes": [
                    {"numero_questao": 1, "resposta_aluno": "C", "resposta_correta": "C"},
                    {"numero_questao": 2, "resposta_aluno": "A", "resposta_correta": "B"},
                ]
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["questoes"]) == 2
        assert data["questoes"][0]["acerto"] is True
        assert data["questoes"][1]["acerto"] is False


class TestRedacao:
    def test_upload_redacao(self):
        _register()
        token = _login()
        resp = client.post(
            "/api/redacoes/upload",
            files={"file": ("redacao.png", b"handwritten essay text", "image/png")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert "texto_ocr" in resp.json()

    def test_list_redacoes(self):
        _register()
        token = _login()
        resp = client.get("/api/redacoes/", headers=_auth_header(token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDashboard:
    def test_dashboard(self):
        _register()
        token = _login()
        resp = client.get("/api/dashboard/", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "nota_estimada" in data
        assert "plano_temporal" in data
        assert data["plano_temporal"]["carga_diaria_questoes"] > 0


class TestFlashcards:
    def test_list_pendentes(self):
        _register()
        token = _login()
        resp = client.get("/api/flashcards/pendentes", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_gerar_flashcards(self):
        _register()
        token = _login()
        hid = _seed_habilidade()
        resp = client.post(
            "/api/flashcards/gerar",
            json={"habilidade_id": hid, "quantidade": 2},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 2
        assert "pergunta" in resp.json()[0]

    def test_revisar(self):
        _register()
        token = _login()
        hid = _seed_habilidade()
        gen = client.post(
            "/api/flashcards/gerar",
            json={"habilidade_id": hid, "quantidade": 1},
            headers=_auth_header(token),
        )
        fid = gen.json()[0]["id"]

        resp = client.post(
            f"/api/flashcards/{fid}/revisar",
            json={"dificuldade": "facil"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["intervalo_dias"] > 1


class TestHealth:
    def test_root(self):
        resp = client.get("/api")
        assert resp.status_code == 200
        assert resp.json()["message"]

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestAIProvider:
    def test_fallback_ocr(self):
        from app.services.ai_provider.fallback_ocr import get_fallback_provider

        provider = get_fallback_provider()
        assert provider.ocr_image is not None

    def test_fallback_classify(self):
        import asyncio

        from app.services.ai_provider.fallback_ocr import get_fallback_provider

        provider = get_fallback_provider()
        result = asyncio.run(
            provider.classify_question("Questão de matemática sobre cálculo")
        )
        assert "area" in result

    def test_fallback_essay(self):
        import asyncio

        from app.services.ai_provider.fallback_ocr import get_fallback_provider

        provider = get_fallback_provider()
        result = asyncio.run(provider.correct_essay("Redação sobre educação"))
        assert result["nota_total"] > 0

    def test_fallback_detect(self):
        import asyncio

        from app.services.ai_provider.fallback_ocr import get_fallback_provider

        provider = get_fallback_provider()
        result = asyncio.run(provider.detect_exam_structure(b"test"))
        assert result["total_questoes"] == 45

    def test_fallback_flashcard(self):
        import asyncio

        from app.services.ai_provider.fallback_ocr import get_fallback_provider

        provider = get_fallback_provider()
        result = asyncio.run(provider.generate_flashcard("Habilidade H1"))
        assert "pergunta" in result
        assert "resposta" in result
