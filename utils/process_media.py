import base64
import os

_MEDIA_MIME_TYPES = {
    # ------ Image formats ------
    '.png':  ('image', 'image/png'),
    '.jpg':  ('image', 'image/jpeg'),
    '.jpeg': ('image', 'image/jpeg'),
    '.gif':  ('image', 'image/gif'),
    '.webp': ('image', 'image/webp'),
    '.bmp':  ('image', 'image/bmp'),

    # ------ Audio formats ------
    '.wav':  ('audio', 'wav'), 
    '.mp3':  ('audio', 'mp3'),
}

def build_media_payload(file_path: str) -> dict:
    """
    Read a local media file (image or audio) and convert it into a valid input payload for the LLM.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    extension = os.path.splitext(file_path)[1].lower()
    media_category, mime_or_format = _MEDIA_MIME_TYPES.get(extension, ('unknown', 'application/octet-stream'))

    if media_category == 'unknown':
        print(f"Warning: Unknown extension '{extension}'. It might not be processed correctly.")

    # Read and Base64 encode the file
    with open(file_path, "rb") as f:
        encoded_data = base64.b64encode(f.read()).decode("utf-8")

    # 2. Return the appropriate dictionary structure based on the media type
    if media_category == 'image':
        # Image format: Data URI (OpenAI compatible)
        data_uri = f"data:{mime_or_format};base64,{encoded_data}"
        return {
            "type": "image_url",
            "image_url": {"url": data_uri}
        }

    elif media_category == 'audio':
        # Audio format: input_audio (OpenAI compatible)
        return {
            "type": "input_audio",
            "input_audio": {
                "data": encoded_data,
                "format": mime_or_format
            }
        }
    else:
        # Fallback for unsupported formats
        return {"type": "text", "text": f"[Attached unsupported file: {file_path}]"}