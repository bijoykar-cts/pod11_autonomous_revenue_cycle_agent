import json
from pathlib import Path

from fastapi import APIRouter, Request

from app.api.schemas import (
    CodeRequest,
    CodingEnvelope,
    DemoUser,
    HealthData,
    HealthEnvelope,
    SampleCase,
    SamplesEnvelope,
    UsersEnvelope,
)
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
