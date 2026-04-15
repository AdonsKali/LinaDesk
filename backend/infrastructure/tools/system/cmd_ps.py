import subprocess
import threading
import queue
import time
from backend.core.schemas import ToolSchemaOut

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
            bufsize=1
        )

        self.queue = queue.Queue()
        self._start_reader()

    # ================= INTERNAL =================

    def _start_reader(self):
        def reader():
            for line in self.proc.stdout:
                self.queue.put(line)
        threading.Thread(target=reader, daemon=True).start()


    def _check_security(self, cmd: str):
        cmd_lower = cmd.lower()
        for bad in self.BLOCKED_COMMANDS:
            if bad in cmd_lower:
                raise RuntimeError(f"Blocked dangerous command: {bad}")

    # ================= PUBLIC =================

    def execute(self, command: str, timeout=20.0) -> dict:
        """
        Execute command safely and return JSON-like result
        """
        self._check_security(command)

        marker = "__AI_DONE__"
        full = f"{command}\necho {marker}\n"

        self.proc.stdin.write(full)
        self.proc.stdin.flush()

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
            self.proc.stdin.write("exit\n")
            self.proc.stdin.flush()
        except:
            pass
        self.proc.terminate()
