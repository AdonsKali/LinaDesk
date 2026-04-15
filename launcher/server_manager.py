import threading
import subprocess
import sys
import os
import time
from PySide6.QtCore import QObject, Signal


class ServerManager(QObject):
    server_started = Signal()
    server_stopped = Signal()
    server_error = Signal(str)
    server_pid_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.debug_mode = False
        self.process = None
        self.host = "127.0.0.1"
        self.port = 8000
        
    def start(self):
        """Запуск сервера в отдельном консольном окне"""
        def run_server():
            try:
                cmd = [
                    sys.executable,
                    "backend/run_server.py",
                    "--debug" if self.debug_mode else ""
                ]
                
                if sys.platform == "win32":
                    self.process = subprocess.Popen(
                        cmd,
                        cwd=os.getcwd()
                    )
                else:
                    terminal = self._get_linux_terminal()
                    if terminal:
                        cmd = [terminal, "-e"] + [" ".join(cmd)]
                        self.process = subprocess.Popen(cmd)
                    else:
                        self.process = subprocess.Popen(cmd)
                
                if self._wait_for_server():
                    self.server_started.emit()
                if self.process:
                    self.server_pid_changed.emit(self.process.pid)
                else:
                    self.server_error.emit("Сервер не ответил на запросы")
                    
            except Exception as e:
                self.server_error.emit(f"Ошибка запуска: {str(e)}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    
    def _get_linux_terminal(self):
        terminals = ['xterm', 'gnome-terminal', 'konsole', 'xfce4-terminal']
        for terminal in terminals:
            if subprocess.call(['which', terminal], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE) == 0:
                return terminal
        return None
    
    def _wait_for_server(self, timeout=10):
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(0.5)
        
        return False
    
    def stop(self):
        if self.process:
            if sys.platform == "win32":
                import signal
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()
            
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            self.process = None
            self.server_stopped.emit()
    
    def is_running(self):
        import requests
        try:
            response = requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
            return response.status_code == 200
        except:
            return False