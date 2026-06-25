# ICD-10 Coding Pipeline PoC Development Plan

## 1. Product Direction

Build a local hackathon MVP for an ICD-10 clinical coding assistant. The system accepts encounter text, runs a three-stage coding pipeline, validates recommendations against a local ICD corpus, and presents recommendations in a plain HTML/JavaScript review UI.

Primary optimization order:

1. Safety
2. Speed
3. Demo polish

This is a hackathon MVP, not a production PHI system. The user-selected MVP allows full local note persistence, but that must be treated as local-demo-only behavior with clear warnings and no external logging. Production use with real PHI would require authentication hardening, encryption, audit logs, access controls, retention policy, and compliance review.

## 2. Locked Decisions From Interview

- Validation source of truth: local ICD corpus.
- Pinecone role: primary retrieval layer when available.
- MySQL role: fallback path only if Pinecone fails during development; otherwise not part of MVP.
- Corpus ingestion target: local JSON indexes, Pinecone index, optional MySQL fallback tables.
- LLM mode: no LLM in MVP; local/mock execution.
- Agent implementation: deterministic/mock agents first.
- Agent prompts: not relevant for MVP because no LLM execution.
- Coding surfaces: separate backend modules for diagnosis and procedure, one public API surface.
- API batch support: no; single note only.
- Specificity policy: return supported general/family candidate with a specificity warning rather than inventing unsupported detail.
- Validation strictness: reject only nonexistent codes in MVP.
- Code status model: `suggested`, `accepted`, `rejected`, `needs_documentation`.
- Auto-accept policy: allowed only when all checks pass.
- CM/PCS conflict policy: suppress lower-confidence side.
- Confidence model: composite `confidence` plus `retrieval_score`, `evidence_score`, and `validation_score`.
- Missing corpus code status: `not_in_configured_corpus`.
- Evidence format: character offsets plus redacted snippets.
- Debug output: only timing and trace IDs.
- Debug access: local development config only.
- UI: plain HTML/JavaScript.
- UI is core MVP.
- Demo users: coder, physician reviewer, revenue cycle manager, admin.
- Credentials: checked-in `DEMO_CREDENTIALS.md` for hackathon use.
- Sample cases: general sample data only; include tricky cases such as negation, ruled-out diagnoses, family history, and history-of diagnoses.
- Testing target: schema and validation guarantees, not exact-code accuracy.
- Audit logging: not in MVP.
- Docker/Compose: not in MVP; local Python and browser commands only.

## 3. MVP Capability Contract

### Actors

- `coder`: reviews generated recommendations and sees accepted/suggested/rejected statuses.
- `physician_reviewer`: reviews documentation gaps and evidence support.
- `revenue_cycle_manager`: reviews summary metrics and denial-risk signals.
- `admin`: can use local debug mode when enabled by config.

### User Surfaces

- Plain browser UI served by FastAPI static files.
- API docs through FastAPI OpenAPI.
- Checked-in demo credentials file.
- Local sample cases loaded from source-controlled JSON.

### Core Flow

1. User selects a sample user role or enters demo credentials.
2. User opens a single sample case or pastes encounter text.
3. UI submits the note to the coding API.
4. Orchestrator runs extraction, recommendation, and validation.
5. API returns diagnosis and procedure recommendations.
6. UI shows recommendations, evidence offsets, redacted snippets, confidence components, and review flags.
7. Recommendations are auto-accepted only when all MVP checks pass.

## 4. Proposed Repository Structure

```text
app/
  __init__.py
  main.py
  api/
    __init__.py
    routes.py
    schemas.py
  agents/
    __init__.py
    extraction_agent.py
    diagnosis_agent.py
    procedure_agent.py
    validation_agent.py
  corpus/
    __init__.py
    loader.py
    models.py
    normalizer.py
    validator.py
  orchestration/
    __init__.py
    coding_pipeline.py
    trace.py
  retrieval/
    __init__.py
    local_retriever.py
    pinecone_retriever.py
    mysql_fallback_plan.py
  storage/
    __init__.py
    local_store.py
  static/
    index.html
    app.js
    styles.css
data/
  corpus/
    icd10_cm_sample.json
    icd10_pcs_sample.json
    corpus_manifest.json
  samples/
    sample_cases.json
DEMO_CREDENTIALS.md
requirements.txt
pytest.ini
tests/
  test_api_schema.py
  test_corpus_validation.py
  test_pipeline_statuses.py
  test_debug_contract.py
```

## 5. API Contract

### `POST /api/code`

Single public coding endpoint. Internally dispatches to diagnosis and procedure modules.

Request:

```json
{
  "case_id": "sample-negation-001",
  "note_text": "Patient has history of hypertension. Pneumonia ruled out.",
  "corpus_version": "configured-default",
  "include_debug": false,
  "persist_note": true
}
```

Response:

```json
{
  "success": true,
  "data": {
    "case_id": "sample-negation-001",
    "corpus_version": "configured-default",
    "diagnosis_codes": [
      {
        "code": "I10",
        "description": "Essential (primary) hypertension",
        "code_system": "ICD-10-CM",
        "status": "accepted",
        "validation_status": "valid",
        "confidence": 0.91,
        "retrieval_score": 0.88,
        "evidence_score": 0.94,
        "validation_score": 1.0,
        "evidence": [
          {
            "start": 24,
            "end": 36,
            "redacted_snippet": "history of hypertension"
          }
        ],
        "review_flags": []
      }
    ],
    "procedure_codes": [],
    "review_flags": [
      {
        "type": "negated_condition",
        "message": "Pneumonia was ruled out and should not be coded."
      }
    ],
    "debug": null
  },
  "error": null
}
```

### `GET /api/samples`

Returns sample cases only. Sample cases should be synthetic.

### `GET /api/users`

Returns demo user roles and display names only. Passwords remain documented in `DEMO_CREDENTIALS.md`.

### `GET /api/health`

Returns local service health and corpus availability.

## 6. Data Contracts

### ICD Corpus Record

```json
{
  "code": "I10",
  "code_system": "ICD-10-CM",
  "description": "Essential (primary) hypertension",
  "includes": [],
  "excludes": [],
  "corpus_version": "configured-default",
  "active": true
}
```

### Recommendation Statuses

- `suggested`: valid candidate, but not enough evidence or confidence for auto-acceptance.
- `accepted`: all MVP checks pass.
- `rejected`: invalid or contradicted by note context.
- `needs_documentation`: likely coding opportunity but the note lacks enough specificity or support.

### Validation Statuses

- `valid`: code exists in configured corpus.
- `not_in_configured_corpus`: code was proposed but is absent from the configured corpus.

## 7. Phase Plan

### Phase 0: Project Scaffold

Goal: create a runnable FastAPI project with tests.

Tasks:

- Add `requirements.txt` with `fastapi`, `uvicorn`, `pydantic`, `pytest`, and optional `pinecone`.
- Add `pytest.ini`.
- Create `app/main.py` with FastAPI app factory.
- Create `app/api/routes.py` with `/api/health`.
- Create `app/api/schemas.py` with response envelope models.
- Add `tests/test_api_schema.py`.

Acceptance criteria:

- `python -m pytest` runs.
- `uvicorn app.main:app --reload` starts locally.
- `/api/health` returns `success: true`.

### Phase 1: Corpus Loader And Deterministic Validation

Goal: make local ICD corpus the canonical source of truth.

Tasks:

- Create `data/corpus/icd10_cm_sample.json`.
- Create `data/corpus/icd10_pcs_sample.json`.
- Create `data/corpus/corpus_manifest.json` with configurable version metadata.
- Implement `app/corpus/models.py`.
- Implement `app/corpus/loader.py`.
- Implement `app/corpus/normalizer.py`.
- Implement `app/corpus/validator.py`.
- Add `tests/test_corpus_validation.py`.

Acceptance criteria:

- Valid codes return `valid`.
- Unknown codes return `not_in_configured_corpus`.
- Corpus version is configurable.
- Tests cover schema and validation behavior.

### Phase 2: Deterministic Three-Agent Pipeline

Goal: implement mock/deterministic agents that exercise the full architecture without LLM dependency.

Tasks:

- Implement `app/agents/extraction_agent.py`.
- Implement `app/agents/diagnosis_agent.py`.
- Implement `app/agents/procedure_agent.py`.
- Implement `app/agents/validation_agent.py`.
- Implement `app/orchestration/coding_pipeline.py`.
- Implement `app/orchestration/trace.py`.
- Add `tests/test_pipeline_statuses.py`.

Agent behavior:

- Extraction identifies simple condition/procedure phrases, negation, history-of, ruled-out conditions, and documentation gaps.
- Diagnosis agent proposes CM candidates from extracted findings.
- Procedure agent proposes PCS candidates only when procedure evidence is explicit.
- Validation agent checks proposed codes against local corpus.
- Lower-confidence CM/PCS conflict side is suppressed.
- Auto-accept happens only when all checks pass.

Acceptance criteria:

- Pipeline returns diagnosis and procedure arrays.
- Negated and ruled-out findings are flagged, not accepted.
- General/family candidates carry specificity warnings.
- Unknown codes become `not_in_configured_corpus`.

### Phase 3: Retrieval Layer

Goal: add retrieval abstraction while keeping MVP reliable without external dependencies.

Tasks:

- Implement `app/retrieval/local_retriever.py` using local corpus keyword matching.
- Add `app/retrieval/pinecone_retriever.py` interface and config checks.
- Add `app/retrieval/mysql_fallback_plan.py` as a documented placeholder only.
- Wire pipeline to use local retrieval by default in no-LLM mode.
- Make Pinecone optional in config.

Acceptance criteria:

- MVP works without Pinecone.
- Pinecone integration path is isolated and does not break local tests.
- MySQL fallback remains planned unless Pinecone fails during development.

### Phase 4: API Endpoint

Goal: expose the full single-note coding flow.

Tasks:

- Add `POST /api/code`.
- Add request and response Pydantic schemas.
- Add `include_debug` support that returns only timing and trace IDs in local development config.
- Add `persist_note` support for local demo mode.
- Add safe error responses that do not echo note text.
- Add schema tests in `tests/test_api_schema.py`.

Acceptance criteria:

- API accepts one note at a time.
- Response follows the envelope contract.
- Debug response does not include prompts, raw note text, retrieval hits, or agent internals.
- Errors do not leak submitted note text.

### Phase 5: Local Storage And Demo Cases

Goal: support the selected local demo workflow while keeping sample data synthetic.

Tasks:

- Implement `app/storage/local_store.py` using local JSON files or SQLite if needed.
- Add `data/samples/sample_cases.json`.
- Include sample categories:
  - straightforward diagnosis
  - explicit procedure
  - negated condition
  - ruled-out diagnosis
  - family history
  - history-of diagnosis
  - insufficient specificity
  - invalid-code simulation
- Add `GET /api/samples`.
- Add `DEMO_CREDENTIALS.md` with hackathon-only users:
  - coder
  - physician reviewer
  - revenue cycle manager
  - admin

Acceptance criteria:

- Sample cases load in UI.
- Real submitted notes can be persisted locally only when `persist_note` is true.
- UI and docs warn that local persistence is not production PHI compliance.

### Phase 6: Plain HTML/JavaScript UI

Goal: create a functional coder review workbench without a frontend build system.

Tasks:

- Create `app/static/index.html`.
- Create `app/static/app.js`.
- Create `app/static/styles.css`.
- Serve static UI from FastAPI.
- Add role selector/login using demo credentials.
- Add sample case selector.
- Add note input area.
- Add recommendation table with status, code, description, confidence components, evidence offsets, redacted snippets, and review flags.
- Add warning banner for local demo PHI risk.

Acceptance criteria:

- User can open UI in browser from local FastAPI server.
- User can load a sample case and run coding.
- User can paste a note and run coding.
- UI clearly distinguishes accepted, suggested, rejected, and needs-documentation codes.
- UI shows all applicable failure modes.

### Phase 7: Verification And Hackathon Readiness

Goal: validate the MVP path end to end.

Tasks:

- Run `python -m pytest`.
- Run local server.
- Manually test:
  - `/api/health`
  - `/api/samples`
  - `/api/code`
  - UI sample case flow
  - pasted note flow
  - debug disabled/enabled behavior
- Confirm no external calls are required for MVP.
- Confirm no raw note text appears in errors or debug output.

Acceptance criteria:

- Tests pass.
- UI demo works locally.
- Known failure modes are visible:
  - invalid code
  - unsupported evidence
  - low confidence
  - conflicting recommendations
  - missing documentation
  - negation and ruled-out diagnosis

## 8. Test Plan

### `tests/test_api_schema.py`

- `test_health_response_envelope`
- `test_code_request_accepts_single_note`
- `test_code_response_contains_statuses_and_scores`
- `test_code_error_does_not_echo_note_text`

### `tests/test_corpus_validation.py`

- `test_known_cm_code_is_valid`
- `test_known_pcs_code_is_valid`
- `test_unknown_code_is_not_in_configured_corpus`
- `test_corpus_version_is_loaded_from_manifest`

### `tests/test_pipeline_statuses.py`

- `test_negated_condition_is_not_accepted`
- `test_ruled_out_condition_is_flagged`
- `test_specificity_gap_returns_needs_documentation`
- `test_all_checks_pass_allows_auto_accept`
- `test_cm_pcs_conflict_suppresses_lower_confidence_side`

### `tests/test_debug_contract.py`

- `test_debug_false_returns_null_debug`
- `test_debug_true_returns_trace_id_and_timing_only`
- `test_debug_does_not_return_raw_note_text`

## 9. Configuration

Use environment variables with safe defaults:

```text
APP_ENV=local
CORPUS_VERSION=configured-default
ENABLE_DEBUG=false
ENABLE_LOCAL_NOTE_PERSISTENCE=true
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
PINECONE_ENABLED=false
```

Do not commit real API keys or real PHI.

## 10. Known MVP Tradeoffs

- No LLM means code recommendations are deterministic and limited.
- Validation checks only code existence, not full coding guideline compliance.
- Full local note persistence is not production-safe.
- No audit log by user decision.
- No Docker or deployment packaging.
- Pinecone and MySQL fallback are architecture paths, not required for the first local demo.
- Exact expected ICD code accuracy is not a test target; schema and validation behavior are.

## 11. Post-MVP Hardening

These are intentionally outside the hackathon MVP:

- Add real LLM adapter and prompt versioning.
- Add full official ICD import pipeline.
- Add includes/excludes/guideline-aware validation.
- Add PHI-safe authentication, authorization, encryption, audit logs, and retention policy.
- Add persistent database with migrations.
- Add MySQL fallback retrieval if Pinecone is unavailable.
- Add production deployment packaging.
- Add coder override feedback loop.
- Add batch coding and asynchronous processing.
