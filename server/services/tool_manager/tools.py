import os
from pathlib import Path
import webbrowser
import requests
import subprocess
import shlex
import sys
from bs4 import BeautifulSoup
from ddgs import DDGS
from typing import Dict, Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


def run(path: str) -> Dict[str, Any]:
    """Открытие файла или ссылки - работает на КЛИЕНТЕ"""
    try:
        if path.startswith(('http://', 'https://')):
            webbrowser.open(path)
            return {
                "status": "ok",
                "msg": f"Ссылка {path} открыта",
            }
        else:
            # Проверяем существует ли файл
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "msg": f"Файл не найден: {path}",
                }
            
            # Для Windows используем os.startfile
            if os.name == 'nt':
                os.startfile(path)
            else:
                # Для Linux/Mac
                import subprocess
                subprocess.run(['xdg-open', path])
            
            return {
                "status": "ok",
                "data": {"path": path, "type": "file"}
            }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка при открытии {path}: {str(e)}",
        }


def read(path: str) -> Dict[str, Any]:
    """Чтение файла - работает на КЛИЕНТЕ"""
    try:
        # Проверяем существует ли файл
        if not os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Файл не найден: {path}",
                "data": {"path": path}
            }
        
        # Проверяем размер файла (ограничиваем большие файлы)
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return {
                "status": "error",
                "msg": f"Файл слишком большой: {file_size} байт",
            }
        
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            return {
                "status": "success",
                "msg": f"Файл {path} успешно прочитан",
                "data": {
                    "path": path,
                    "content": content,
                    "size": len(content),
                    "lines": len(content.split('\n'))
                }
            }
    except UnicodeDecodeError:
        # Пробуем другие кодировки
        try:
            with open(path, 'r', encoding='cp1251') as file:
                content = file.read()
                return {
                    "status": "success",
                    "msg": f"Файл {path} прочитан в кодировке cp1251",
                    "data": {
                        "path": path,
                        "content": content,
                        "encoding": "cp1251"
                    }
                }
        except Exception as e:
            return {
                "status": "error",
                "msg": f"Ошибка кодировки файла {path}: {str(e)}",
                "data": {"path": path}
            }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка при чтении {path}: {str(e)}",
            "data": {"path": path, "error": str(e)}
        }


def delete_file(path: str) -> Dict[str, Any]:
    """Удаление файла - работает на КЛИЕНТЕ"""
    try:
        # Проверяем существует ли файл
        if not os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Файл не найден: {path}",
                "data": {"path": path}
            }
        
        # Удаляем файл
        os.remove(path)
        
        return {
            "status": "success",
            "msg": f"Файл {path} успешно удалён",
            "data": {"path": path}
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка при удалении {path}: {str(e)}",
            "data": {"path": path, "error": str(e)}
        }


def mk_dir(path: str) -> Dict[str, Any]:
    """Создание директории - работает на КЛИЕНТЕ"""
    try:
        # Проверяем не существует ли уже
        if os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Директория уже существует: {path}",
                "data": {"path": path}
            }
        
        os.makedirs(path, exist_ok=True)
        
        return {
            "status": "ok",
            "data": {"path": path}
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка при создании директории {path}: {str(e)}",
            "data": {"path": path, "error": str(e)}
        }


def mk_file(path: str, data: str = "") -> Dict[str, Any]:
    """Создание файла - работает на КЛИЕНТЕ"""
    try:
        # Проверяем не существует ли уже
        if os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Файл уже существует: {path}",
                "data": {"path": path}
            }
        
        # Создаём родительские директории если нужно
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # Создаём файл
        Path(path).write_text(data, encoding="utf-8")
        
        return {
            "status": "ok",
            "msg": f"Файл {path} успешно создан",
            "data": {
                "path": path,
                "size": len(data),
                "lines": len(data.split('\n')) if data else 0
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка создании файла {path}: {str(e)}",
        }


def duckduckgo_search_with_rich_snippets(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Поиск в интернете - работает на КЛИЕНТЕ"""
    try:
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=num_results))

            for res in search_results:
                url = res.get("href", "")
                title = res.get("title", "Без заголовка")
                snippet = res.get("body", "")
                summary = snippet

                # Пробуем получить больше информации с страницы
                try:
                    if url:
                        page = requests.get(url, headers=HEADERS, timeout=5)
                        soup = BeautifulSoup(page.text, "html.parser")

                        # Meta description
                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        if meta_desc and meta_desc.get("content"):
                            summary += f" | Описание: {meta_desc['content'][:200]}"

                        # First paragraph
                        first_paragraph = soup.find("p")
                        if first_paragraph:
                            summary += f" | Абзац: {first_paragraph.get_text(strip=True)[:200]}"

                except Exception as e:
                    summary += f" | [Ошибка парсинга: {str(e)[:50]}]"

                results.append({
                    "title": title,
                    "url": url,
                    "summary": summary[:500],  # Ограничиваем длину
                    "snippet": snippet[:300]
                })

        return {
            "status": "ok",
            "msg": f"Найдено {len(results)} результатов",
            "data": {
                "results": results
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка поиска: {str(e)}",
        }


def list_directory(path: str = "."):
    """Список файлов в директории"""
    try:
        if not os.path.exists(path):
            return {
                "status": "error",
                "msg": f"Директория не найдена: {path}",
            }
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else 0
            
            items.append({
                "name": item,
                "size": size,
            })
        
        return {
            "status": "ok",
            "msg": f"Найдено {len(items)}",
            "items": items[:50] 
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка при чтении директории {path}: {str(e)}",
            "data": {"path": path, "error": str(e)}
        }


def execute_cmd(command: str) -> dict:
    # Список кодировок для Windows (в порядке приоритета)
    windows_encodings = ['cp866', 'cp1251', 'utf-8', 'ascii']
    timeout: int = 30
    try:
        if sys.platform == "win32":
            full_command = f"cmd /c {command}"
        else:
            full_command = command
        
        # Сначала выполняем без декодирования
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=False,
            timeout=timeout
        )
        
        output = None
        error = None
        used_encoding = None
        
        # Пробуем разные кодировки для вывода
        if sys.platform == "win32":
            encodings_to_try = windows_encodings
        else:
            encodings_to_try = ['utf-8', 'ascii', 'latin-1']
        
        for enc in encodings_to_try:
            try:
                output = result.stdout.decode(enc, errors='strict')
                error = result.stderr.decode(enc, errors='strict')
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        
        # Если все кодировки не подошли, используем replace
        if output is None:
            used_encoding = windows_encodings[0] if sys.platform == "win32" else 'utf-8'
            output = result.stdout.decode(used_encoding, errors='replace')
            error = result.stderr.decode(used_encoding, errors='replace')
        if error:
            return {
                "status": "ok",
                "output": output[:100],
                "error": error
            }
        else:
            return {
                "status": "ok",
                "output": output[:100],
            }
        
    except Exception as e:
        return {
            "status": "error",
            "output": "",
            "error": str(e),
        }

def execute_ps(
    command: str, 
    wait: bool = True,
    admin: bool = False
):
    try:
        if sys.platform != "win32":
            return {
                "status": "error",
                "msg": "Функция работает только на Windows"
            }
        
        # Экранируем кавычки в команде
        safe_command = command.replace('"', '\\"')
        
        if admin:
            # Для запуска от администратора
            import ctypes
            import win32con
            import win32process
            import win32api
            
            # Создаем команду
            ps_cmd = f'powershell -NoExit -ExecutionPolicy Bypass -Command "{safe_command}"'
            
            # Запускаем с повышенными привилегиями
            win32process.CreateProcess(
                None,
                ps_cmd,
                None,
                None,
                0,
                win32con.CREATE_NEW_CONSOLE,
                None,
                None,
                win32process.STARTUPINFO()
            )
            
            return {
                "status": "ok",
                "msg": "Запуск с правами администратора запрошен"
            }
        
        elif wait:
            # Запуск с ожиданием завершения
            result = subprocess.run(
                ['powershell', '-Command', safe_command],
                capture_output=True,
                text=True,
                encoding='utf-8',
                shell=True
            )
            
            return {
                "status": "ok",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        
        else:
            # Запуск в новом окне без ожидания
            ps_cmd = f'powershell -NoExit -ExecutionPolicy Bypass -Command "{safe_command}"'
            
            subprocess.Popen(
                ps_cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            
            return {
                "status": "ok",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Ошибка выполнения PowerShell: {str(e)}"
        }
        