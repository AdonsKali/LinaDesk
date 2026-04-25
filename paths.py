from pathlib import Path


BASE_DIR = Path(__name__).resolve().parent

#Client
SRC = BASE_DIR / "client"
MEDIA = SRC / "src" / "media"

#Backend 
BACKEND = BASE_DIR / "backend"

MODELS = BASE_DIR / "infrastructure" / "models"
VOSK_MODEL = BASE_DIR  / "infrastructure" / "models" / "vosk-model"
CONFIGS = BACKEND / "core" / "agent" / "configs"