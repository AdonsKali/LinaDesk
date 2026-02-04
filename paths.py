from pathlib import Path


BASE_DIR = Path(__name__).resolve().parent
SRC = BASE_DIR / "app" / "src"
MODELS = BASE_DIR / "server" / "models"
MEDIA = SRC / "media"
TESTS = BASE_DIR / "app" / "tests"
VOSK_MODEL = BASE_DIR  / "server" / "models" / "vosk-model"