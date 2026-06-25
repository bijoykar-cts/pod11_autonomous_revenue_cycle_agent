import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.corpus.models import Corpus, CorpusRecord
from app.corpus.normalizer import normalize_code, normalize_code_system


ROOT_DIR = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT_DIR / "data" / "corpus"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_records(path: Path, default_version: str) -> list[CorpusRecord]:
    rows = _read_json(path)
    records: list[CorpusRecord] = []
    for row in rows:
        records.append(
            CorpusRecord(
                code=normalize_code(row["code"]),
                code_system=normalize_code_system(row["code_system"]),
                description=str(row["description"]),
                includes=tuple(row.get("includes", [])),
                excludes=tuple(row.get("excludes", [])),
                corpus_version=str(row.get("corpus_version", default_version)),
                active=bool(row.get("active", True)),
            )
        )
    return records


@lru_cache(maxsize=8)
def load_default_corpus(version: str = "configured-default") -> Corpus:
    manifest = _read_json(CORPUS_DIR / "corpus_manifest.json")
    corpus_version = str(manifest.get("version", version))
    records = [
        *_load_records(CORPUS_DIR / "icd10_cm_sample.json", corpus_version),
        *_load_records(CORPUS_DIR / "icd10_pcs_sample.json", corpus_version),
    ]
    return Corpus(
        version=corpus_version,
        records={(record.code, record.code_system): record for record in records},
    )
