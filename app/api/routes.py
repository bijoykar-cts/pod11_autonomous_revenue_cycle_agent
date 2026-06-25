import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.api.schemas import (
    CodeRequest,
    CodingEnvelope,
    DemoUser,
    DocumentExtractData,
    DocumentExtractEnvelope,
    HealthData,
    HealthEnvelope,
    SampleCase,
    SamplesEnvelope,
    UsersEnvelope,
)
from app.documents.extractor import DocumentExtractionError, extract_document_text
from app.orchestration.coding_pipeline import CodingPipeline
from app.storage.local_store import LocalStore


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLES_PATH = ROOT_DIR / "data" / "samples" / "sample_cases.json"

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthEnvelope)
def health(request: Request) -> HealthEnvelope:
    corpus = request.app.state.corpus
    settings = request.app.state.settings
    return HealthEnvelope(
        success=True,
        data=HealthData(
            status="ok" if corpus.record_count > 0 else "degraded",
            corpus_version=corpus.version,
            corpus_records=corpus.record_count,
            pinecone_enabled=settings.pinecone_enabled,
        ),
        error=None,
    )


@router.get("/samples", response_model=SamplesEnvelope)
def samples() -> SamplesEnvelope:
    with SAMPLES_PATH.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)
    return SamplesEnvelope(
        success=True,
        data=[SampleCase(**row) for row in rows],
        error=None,
    )


@router.get("/users", response_model=UsersEnvelope)
def users() -> UsersEnvelope:
    return UsersEnvelope(
        success=True,
        data=[
            DemoUser(username="coder.demo", display_name="Coder Demo", role="coder"),
            DemoUser(
                username="physician.demo",
                display_name="Physician Reviewer Demo",
                role="physician_reviewer",
            ),
            DemoUser(
                username="rcm.demo",
                display_name="Revenue Cycle Manager Demo",
                role="revenue_cycle_manager",
            ),
            DemoUser(username="admin.demo", display_name="Admin Demo", role="admin"),
        ],
        error=None,
    )


@router.post("/code", response_model=CodingEnvelope)
def code(payload: CodeRequest, request: Request) -> CodingEnvelope:
    settings = request.app.state.settings
    corpus = request.app.state.corpus
    if payload.corpus_version is not None and payload.corpus_version != corpus.version:
        raise HTTPException(
            status_code=400,
            detail="Unsupported corpus version",
            headers={"X-Error-Code": "unsupported_corpus_version"},
        )
    if payload.persist_note:
        LocalStore(enabled=settings.enable_local_note_persistence).persist_note(
            case_id=payload.case_id,
            note_text=payload.note_text,
        )
    pipeline = CodingPipeline(corpus=corpus, debug_enabled=settings.local_debug_allowed)
    result = pipeline.run(
        case_id=payload.case_id,
        note_text=payload.note_text,
        include_debug=payload.include_debug,
        persist_note=payload.persist_note,
    )
    return CodingEnvelope(success=True, data=result, error=None)


@router.post("/documents/extract", response_model=DocumentExtractEnvelope)
async def extract_document(file: UploadFile = File(...)) -> DocumentExtractEnvelope:
    filename = file.filename or "uploaded-document"
    content = await file.read()
    try:
        document_type, note_text = extract_document_text(filename, content)
    except DocumentExtractionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail="Document extraction failed",
            headers={"X-Error-Code": exc.code},
        ) from exc
    return DocumentExtractEnvelope(
        success=True,
        data=DocumentExtractData(
            filename=filename,
            document_type=document_type,
            note_text=note_text,
            character_count=len(note_text),
        ),
        error=None,
    )
