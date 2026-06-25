from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app())


def test_health_response_envelope():
    response = make_client().get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert "corpus_version" in body["data"]


def test_code_request_accepts_single_note():
    response = make_client().post(
        "/api/code",
        json={
            "case_id": "api-schema-001",
            "note_text": "Patient has essential hypertension.",
            "include_debug": False,
            "persist_note": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["case_id"] == "api-schema-001"
    assert isinstance(body["data"]["diagnosis_codes"], list)
    assert isinstance(body["data"]["procedure_codes"], list)


def test_code_response_contains_statuses_and_scores():
    response = make_client().post(
        "/api/code",
        json={
            "case_id": "scores-001",
            "note_text": "Patient has essential hypertension.",
            "include_debug": False,
            "persist_note": False,
        },
    )

    recommendation = response.json()["data"]["diagnosis_codes"][0]
    assert recommendation["status"] in {
        "suggested",
        "accepted",
        "rejected",
        "needs_documentation",
    }
    assert recommendation["validation_status"] in {
        "valid",
        "not_in_configured_corpus",
    }
    assert 0 <= recommendation["confidence"] <= 1
    assert 0 <= recommendation["retrieval_score"] <= 1
    assert 0 <= recommendation["evidence_score"] <= 1
    assert 0 <= recommendation["validation_score"] <= 1


def test_code_error_does_not_echo_note_text():
    note = "Patient Jane Example has hypertension and private note text."
    response = make_client().post(
        "/api/code",
        json={"case_id": "bad-note", "note_text": note, "include_debug": "not-bool"},
    )

    assert response.status_code == 422
    body_text = response.text
    assert note not in body_text
    assert "Jane Example" not in body_text
    assert "private note text" not in body_text
