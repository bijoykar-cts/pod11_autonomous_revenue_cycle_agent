import json
from pathlib import Path
from time import time


ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_DATA_DIR = ROOT_DIR / "data" / "local"


class LocalStore:
    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    def persist_note(self, case_id: str, note_text: str) -> None:
        if not self._enabled:
            return
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "case_id": case_id,
            "note_text": note_text,
            "created_at_epoch": time(),
            "warning": "Local demo storage only. Not production PHI compliance.",
        }
        with (LOCAL_DATA_DIR / "submissions.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
