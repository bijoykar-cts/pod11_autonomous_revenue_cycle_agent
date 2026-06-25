from fastapi.testclient import TestClient

from app.main import create_app


def test_debug_false_returns_null_debug():
    client = TestClient(create_app())

    response = client.post(
        "/api/code",
        json={
            "case_id": "debug-off",
            "note_text": "Patient has essential hypertension.",
            "include_debug": False,
            "persist_note": False,
        },
    )

    assert response.json()["data"]["debug"] is None


def test_debug_true_returns_trace_id_and_timing_only(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG", "true")
    client = TestClient(create_app())

    response = client.post(
        "/api/code",
        json={
            "case_id": "debug-on",
            "note_text": "Patient has essential hypertension.",
            "include_debug": True,
            "persist_note": False,
        },
    )

    debug = response.json()["data"]["debug"]
    assert set(debug) == {"trace_id", "timing_ms"}
    assert isinstance(debug["trace_id"], str)
    assert isinstance(debug["timing_ms"], int | float)


def test_debug_does_not_return_raw_note_text(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG", "true")
    note = "Patient John Debug has essential hypertension."
    client = TestClient(create_app())

    response = client.post(
        "/api/code",
        json={
            "case_id": "debug-safe",
            "note_text": note,
            "include_debug": True,
            "persist_note": False,
        },
    )

    assert note not in response.text
    assert "John Debug" not in response.text
