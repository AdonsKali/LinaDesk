from datetime import datetime
from src.core.domain.value_objects.tool import ToolPermission
from src.core.infrastructure.services.tools.base import BaseTool
from src.core.utils.logger import logger
import subprocess
import queue
import time
import threading
logger = logger.get(__name__)


class EchoTool(BaseTool):
    name = "echo"
    description = "Повторяет текст, который ему передали. Полезно для тестирования."
    parameters = {"text": "Текст, который нужно повторить"}
    permissions = [ToolPermission.READ]

    async def execute(self, text: str) -> str:
        logger.info(f"[EchoTool] text={text!r}")
        return f"Echo: {text}"


class GetCurrentTimeTool(BaseTool):
    name = "get_current_time"
    description = "Возвращает текущее время в формате HH:MM:SS."
    parameters = {}
    permissions = [ToolPermission.READ]

    async def execute(self) -> str:
        now = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[GetCurrentTimeTool] time={now}")
        return f"Текущее время: {now}"


class GetCurrentDateTool(BaseTool):
    name = "get_current_date"
    description = "Возвращает текущую дату в формате DD.MM.YYYY."
    parameters = {}
    permissions = [ToolPermission.READ]

    async def execute(self) -> str:
        today = datetime.now().strftime("%d.%m.%Y")
        logger.info(f"[GetCurrentDateTool] date={today}")
        return f"Сегодня: {today}"
    
    
class AIShellController(BaseTool):
    name = "execute_command"
    description = "Выполняет CMD или powershell команду в windows"
    parameters = {
        "command": "Команда", "timeout": "Время исполнения команды"
    }
    permissions = [ToolPermission.EXECUTE, ToolPermission.READ]
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

    async def execute(self, command: str, timeout=20.0):
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

        result = output

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


BUILTIN_TOOLS: list[type[BaseTool]] = [
    EchoTool,
    GetCurrentTimeTool,
    GetCurrentDateTool,
    AIShellController,
]