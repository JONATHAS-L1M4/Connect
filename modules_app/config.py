import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import requests

# =========================
# Config / Boot
# =========================
load_dotenv()

DOMAIN = os.getenv("EVOLUTION_DOMAIN") or ""
requests.packages.urllib3.disable_warnings()  # noqa

# Paths base (BASE_DIR = raiz do projeto; este arquivo está em /modulo)
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Templates externos
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
