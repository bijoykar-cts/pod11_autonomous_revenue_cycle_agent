from io import BytesIO
import zipfile

from fastapi.testclient import TestClient

from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app())


def make_docx(paragraphs: list[str]) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
        + "</w:body></w:document>"
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_extract_txt_document_into_note_text():
    response = make_client().post(
        "/api/documents/extract",
        files={
            "file": (
                "clinical-note.txt",
                b"Patient has essential hypertension.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["filename"] == "clinical-note.txt"
    assert body["data"]["document_type"] == "txt"
    assert body["data"]["note_text"] == "Patient has essential hypertension."


def test_extract_docx_document_into_note_text():
    response = make_client().post(
        "/api/documents/extract",
        files={
            "file": (
                "clinical-note.docx",
                make_docx(["Patient underwent laparoscopic cholecystectomy.", "Essential hypertension noted."]),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    note_text = response.json()["data"]["note_text"]
    assert "laparoscopic cholecystectomy" in note_text
    assert "Essential hypertension" in note_text


def test_reject_unsupported_binary_word_document_safely():
    response = make_client().post(
        "/api/documents/extract",
        files={"file": ("legacy-note.doc", b"binary-data", "application/msword")},
    )

    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "unsupported_document_type"
    assert "binary-data" not in response.text
