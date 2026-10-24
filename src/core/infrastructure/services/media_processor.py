import base64
import logging
import os

logger = logging.getLogger(__name__)


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_AUDIO_EXTENSIONS = {".wav", ".mp3"}
_TEXT_EXTENSIONS = {".txt", ".md", ".log", ".json", ".yaml", ".yml", ".csv", ".py"}

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

_AUDIO_FORMAT_BY_EXT = {
    ".wav": "wav",
    ".mp3": "mp3",
}


class FileMediaProcessor:
    """Обработка локальных файлов → OpenAI-совместимые media parts."""

    def is_image(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in _IMAGE_EXTENSIONS

    def is_audio(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in _AUDIO_EXTENSIONS

    def is_text(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in _TEXT_EXTENSIONS

    def build_media_part(self, file_path: str) -> dict:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Media file not found: {file_path}")
        if os.path.getsize(file_path) > 20 * 1024 * 1024:
            raise ValueError("Максимальный размер вложения — 20 МБ.")

        ext = os.path.splitext(file_path)[1].lower()

        if ext in _IMAGE_EXTENSIONS:
            return self._build_image_part(file_path, ext)
        if ext in _AUDIO_EXTENSIONS:
            return self._build_audio_part(file_path, ext)

        raise ValueError(f"Unsupported media type: {ext}")

    def read_text_file(self, file_path: str, max_chars: int = 6000) -> str:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Text file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(max_chars)
        if len(text) == max_chars:
            text += "\n\n[...truncated...]"
        return text

    def _build_image_part(self, file_path: str, ext: str) -> dict:
        from PIL import Image, ImageOps
        from io import BytesIO
        with Image.open(file_path) as original:
            if original.width * original.height > 25_000_000:
                raise ValueError("Максимальный размер изображения — 25 мегапикселей.")
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((1280, 1280))
            output = BytesIO()
            image.save(output, format="JPEG", quality=85)
        mime = "image/jpeg"
        b64 = base64.b64encode(output.getvalue()).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        }

    def _build_audio_part(self, file_path: str, ext: str) -> dict:
        fmt = _AUDIO_FORMAT_BY_EXT.get(ext, "wav")
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {
            "type": "input_audio",
            "input_audio": {"data": b64, "format": fmt},
        }
