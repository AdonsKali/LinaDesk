import os
from typing import Dict, Any
from pathlib import Path
from backend.core.schemas import ToolSchemaOut

def mk_file(path: str, data: str = "") -> Dict[str, Any]:
    """Создание файла
    Args:
        path: путь к файлу
        data: текст, данные 
    """
    try:
        # Проверяем не существует ли уже
        if os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Файл уже существует: {path}",
            }
        
        # Создаём родительские директории если нужно
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # Создаём файл
        Path(path).write_text(data, encoding="utf-8")
        
        return ToolSchemaOut(
            status='ok',
            msg="File {path} is created",
            data={
                "path": path,
                "size": len(data),
                "lines": len(data.split('\n')) if data else 0
            }
        )
            
        
    except Exception as e:
        return ToolSchemaOut(
            status="error",
            msg=f"Error: {e}"
        )