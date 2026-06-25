from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    corpus_version: str
    enable_debug: bool
    enable_local_note_persistence: bool
    pinecone_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            corpus_version=os.getenv("CORPUS_VERSION", "configured-default"),
            enable_debug=_env_bool("ENABLE_DEBUG", False),
            enable_local_note_persistence=_env_bool(
                "ENABLE_LOCAL_NOTE_PERSISTENCE", False
            ),
            pinecone_enabled=_env_bool("PINECONE_ENABLED", False),
        )

    @property
    def local_debug_allowed(self) -> bool:
        return self.app_env == "local" and self.enable_debug
