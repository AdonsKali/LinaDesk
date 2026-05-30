import os
from pathlib import Path
import sys
from backend.application.decorators import tool
from backend.core.schemas import ToolSchemaOut
import subprocess
import threading
import queue
import time


class AIShellController:
    BLOCKED_COMMANDS = [
        "del ", "rd /s", "format", "shutdown", "reboot", "rm -rf",
        ":(){:|:&};:", "mkfs", "diskpart"
    ]

    def __init__(self, shell="powershell"):
        self.shell = shell
        self.history = []

        if shell == "powershell":
            cmd = ["powershell", "-NoLogo", "-NoExit", "-Command", "-"]
        else:
            cmd = ["cmd"]

        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding='utf-8', 
            errors='replace'   
        )

        self.queue = queue.Queue()
        self._start_reader()

    # ================= INTERNAL =================

    def _start_reader(self):
        def reader():
            for line in self.proc.stdout: #type: ignore
                self.queue.put(line)
        threading.Thread(target=reader, daemon=True).start()


    def _check_security(self, cmd: str):
        cmd_lower = cmd.lower()
        for bad in self.BLOCKED_COMMANDS:
            if bad in cmd_lower:
                raise RuntimeError(f"Blocked dangerous command: {bad}")

    # ================= PUBLIC =================

    def execute(self, command: str, timeout=20.0) -> ToolSchemaOut:
        """
        Execute command safely and return JSON-like result
        """
        self._check_security(command)

        marker = "__AI_DONE__"
        full = f"{command}\necho {marker}\n"

        self.proc.stdin.write(full) #type: ignore
        self.proc.stdin.flush() #type: ignore

        output = []
        start = time.time()

        while True:
            try:
                line = self.queue.get(timeout=0.1)
            except queue.Empty:
                if time.time() - start > timeout:
                    break
                continue

            if marker in line:
                break

            output.append(line)

        result = ToolSchemaOut(
            status='ok',
            msg="".join(output)
        )

        self.history.append(result)
        return result


    def get_history(self):
        return self.history


    def close(self):
        try:
            self.proc.stdin.write("exit\n") #type: ignore
            self.proc.stdin.flush() #type: ignore
        except:
            pass
        self.proc.terminate()
@tool(
    name="mk_file",
    description="Creating a file with data",
    parameters={ 
        "type": "object",
        "properties": {
            "path": {
                "type": "string"
            },
            "data": {
                "type": "string"
            }
        },
        "required": ["path", "data"]
     }
)
def mk_file(path: str, data: str = "") -> ToolSchemaOut:
    """Создание файла
    Args:
        path: путь к файлу
        data: текст, данные 
    """
    try:
        # Проверяем не существует ли уже
        if os.path.exists(path):
            return ToolSchemaOut(
                status='ok',
                msg= f"Файл уже существует: {path}"
            )
        
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
    
ps = AIShellController(shell="powershell")
@tool(
    name="powershell",
    description="Executing a command in the powershell (windows)",
    parameters={ 
        "type": "object",
        "properties": {
            "command": {
                "type": "string"
            },
        },
        "required": ["command"]
     }  
)
def ps_shell(command: str) -> ToolSchemaOut:
    """Execute PowerShell command and return result"""
    try:
        result = ps.execute(command)
        return result
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=f"PowerShell execution error: {str(e)}"
        )
    

from win32api import SetCursorPos, mouse_event
from win32con import MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

@tool(
    name="click_on_ui",
    description="Move and click by cursor",
    parameters={ 
        "type": "object",
        "properties": {
            "x": {
                "type": "int"
            },
            "y": {
                "type": "int"
            },
        },
        "required": ["x", "y"]
     }  
)
def click_on_ui(x: int, y: int) -> ToolSchemaOut:
    try:
        SetCursorPos((x, y))
        time.sleep(0.05)
        mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        return  ToolSchemaOut(
            status='ok',
            msg=f"Clicked on {x}, {y}")
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=f"Error clicking on {x}, {y}: {e}")
        

from pyautogui import screenshot
def _screenshot() -> ToolSchemaOut:
    try:
        img = screenshot("screenshot.png")
        return ToolSchemaOut(
            status='ok',
            msg="Screenshot taken",
            data={
                "image": img
            })
    except Exception as e:
        return ToolSchemaOut(
            status='error',
            msg=f"Error taking screenshot: {e}")
        
        