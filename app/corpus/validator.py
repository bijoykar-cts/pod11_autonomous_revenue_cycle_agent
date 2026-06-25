from app.corpus.models import Corpus, ValidationResult
from app.corpus.normalizer import normalize_code, normalize_code_system


def validate_code(corpus: Corpus, code: str, code_system: str) -> ValidationResult:
    normalized_code = normalize_code(code)
    normalized_system = normalize_code_system(code_system)
    record = corpus.records.get((normalized_code, normalized_system))
    if record is None or not record.active:
        return ValidationResult(
            code=normalized_code,
            code_system=normalized_system,
            description="",
            validation_status="not_in_configured_corpus",
        )
    return ValidationResult(
        code=record.code,
        code_system=record.code_system,
        description=record.description,
        validation_status="valid",
    )
