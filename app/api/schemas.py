from typing import Literal

from pydantic import BaseModel, Field, model_validator


CodeSystem = Literal["ICD-10-CM", "ICD-10-PCS"]
RecommendationStatus = Literal[
    "suggested", "accepted", "rejected", "needs_documentation"
]
ValidationStatus = Literal["valid", "not_in_configured_corpus"]


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: list[dict[str, object]] = Field(default_factory=list)


class HealthData(BaseModel):
    status: Literal["ok", "degraded"]
    corpus_version: str
    corpus_records: int
    pinecone_enabled: bool


class EvidenceItem(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    redacted_snippet: str

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceItem":
        if self.end < self.start:
            raise ValueError("evidence end offset must be >= start offset")
        return self


class ReviewFlag(BaseModel):
    type: str
    message: str


class CodeRecommendation(BaseModel):
    code: str
    description: str
    code_system: CodeSystem
    status: RecommendationStatus
    validation_status: ValidationStatus
    confidence: float = Field(ge=0, le=1)
    retrieval_score: float = Field(ge=0, le=1)
    evidence_score: float = Field(ge=0, le=1)
    validation_score: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    review_flags: list[ReviewFlag] = Field(default_factory=list)


class DebugInfo(BaseModel):
    trace_id: str
    timing_ms: float


class CodingData(BaseModel):
    case_id: str
    corpus_version: str
    diagnosis_codes: list[CodeRecommendation]
    procedure_codes: list[CodeRecommendation]
    review_flags: list[ReviewFlag]
    debug: DebugInfo | None = None


class CodeRequest(BaseModel):
    case_id: str = Field(default="ad-hoc-case", min_length=1, max_length=120)
    note_text: str = Field(min_length=1, max_length=20000)
    corpus_version: str | None = None
    include_debug: bool = False
    persist_note: bool = False


class SampleCase(BaseModel):
    id: str
    title: str
    category: str
    note_text: str
    expected_behavior: str


class DemoUser(BaseModel):
    username: str
    display_name: str
    role: str


class HealthEnvelope(BaseModel):
    success: bool
    data: HealthData | None
    error: ErrorInfo | None


class CodingEnvelope(BaseModel):
    success: bool
    data: CodingData | None
    error: ErrorInfo | None


class SamplesEnvelope(BaseModel):
    success: bool
    data: list[SampleCase] | None
    error: ErrorInfo | None


class UsersEnvelope(BaseModel):
    success: bool
    data: list[DemoUser] | None
    error: ErrorInfo | None
