from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import Settings
from app.corpus.loader import load_default_corpus


STATIC_DIR = Path(__file__).resolve().parent / "static"


def _error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            },
        },
    )


def create_app() -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(
        title="ICD-10 Coding Pipeline PoC",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.corpus = load_default_corpus(settings.corpus_version)
    app.include_router(router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):  # noqa: ANN001
        del request
        details = [
            {
                "loc": [str(part) for part in error.get("loc", [])],
                "msg": str(error.get("msg", "Invalid input")),
                "type": str(error.get("type", "validation_error")),
            }
            for error in exc.errors()
        ]
        return _error_response(422, "validation_error", "Request validation failed.", details)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):  # noqa: ANN001
        del request
        code = exc.headers.get("X-Error-Code") if exc.headers else None
        return _error_response(
            exc.status_code,
            code or "http_error",
            "Request failed.",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):  # noqa: ANN001
        del request, exc
        return _error_response(500, "internal_error", "Internal server error.")

    return app


app = create_app()
