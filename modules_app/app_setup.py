from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR

def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    # Garante que /static/img exista (evita RuntimeError ao montar)
    (STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)

    # Monta arquivos estáticos
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app
