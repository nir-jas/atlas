from fastapi.testclient import TestClient

from atlas_api.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "atlas-api"}


def test_list_notes() -> None:
    response = client.get("/api/v1/notes")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "ai-engineering-foundations"


def test_answer_question() -> None:
    response = client.post("/api/v1/answers", json={"question": "What is RAG?"})

    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert payload["sources"]
