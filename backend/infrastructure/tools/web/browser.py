import webbrowser
from backend.core.schemas import ToolSchemaOut

def open_link(path: str) -> ToolSchemaOut:
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
            msg=str(e)
        )
    return ToolSchemaOut(
            status='ok',
        )