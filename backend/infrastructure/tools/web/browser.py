import webbrowser
from backend.core.schemas import ToolSchemaOut
from typing import Dict, Any

def open_link(path: str) -> Dict[str, Any]:
    """Открытие файла или ссылки
    
    Args: 
        path: путь к файлу или http ссылки 
    """
    try:
        if path.startswith(('http://', 'https://')):
            webbrowser.open(path)
            return ToolSchemaOut(
                status="ok"
            )
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=e
        )