from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[0]

#Presentation
IMAGES = BASE_DIR / "src" / "resources" / "images"

#Core
CORE = BASE_DIR / "src" / "core"
SRC = BASE_DIR / "src"
CONFIG = BASE_DIR / "data" / "settings.json"

#Models
MODELS = SRC / "resources" / "models"

LLM_MODEL = SRC / "resources" / "models" / "llm" / "model.gguf"
MMPROJ = SRC / "resources" / "models" / "llm" / "mmproj-BF16.gguf"
VOSK_MODEL = SRC  / "resources" / "models" / "vosk-model-small-ru-0.22"
EMBEDDING_MODEL = SRC / "resources" / "models" / "embeddings" / "all-MiniLM-L6-v2"