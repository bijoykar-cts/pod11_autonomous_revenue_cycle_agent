from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusRecord:
    code: str
    code_system: str
    description: str
    includes: tuple[str, ...]
    excludes: tuple[str, ...]
    corpus_version: str
    active: bool


@dataclass(frozen=True)
class Corpus:
    version: str
    records: dict[tuple[str, str], CorpusRecord]

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class ValidationResult:
    code: str
    code_system: str
    description: str
    validation_status: str
