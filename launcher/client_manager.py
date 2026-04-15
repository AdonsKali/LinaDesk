from PySide6.QtCore import QObject, Signal
import subprocess
import sys
import os


class ClientManager(QObject):
    client_started = Signal()
    client_stopped = Signal()
    client_error = Signal(str)
    client_pid_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.process = None

    def start(self, language='en', debug=False):
        """Запуск клиентского приложения"""
        try:
            python_path = sys.executable
            client_script = "client/main.py"
            work_dir = os.path.abspath('.')
            
            args = [
                python_path,
                client_script,
                "--lang", language,
            ]
            
            if debug:
                args.extend(["--debug"])
            
            if debug and sys.platform == "win32":
                # При отладке запускаем в отдельном окне консоли на Windows
                self.process = subprocess.Popen(
                    args,
                    cwd=work_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            elif debug and sys.platform != "win32":
                # Для Linux/Mac запускаем в отдельном терминале
                terminal = self._get_linux_terminal()
                if terminal:
                    full_cmd = " ".join(args)
                    self.process = subprocess.Popen([terminal, "-e", "bash", "-c", f"{full_cmd}; exec bash"])
                else:
                    # Если не найден подходящий терминал, запускаем в фоновом режиме
                    self.process = subprocess.Popen(
                        args,
                        cwd=work_dir,
                        preexec_fn=os.setpgrp
                    )
            else:
                # Без отладки запускаем в фоновом режиме
                if sys.platform == "win32":
                    self.process = subprocess.Popen(
                        args,
                        cwd=work_dir,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    self.process = subprocess.Popen(
                        args,
                        cwd=work_dir,
                        preexec_fn=os.setpgrp
                    )
            
            if self.process:
                self.client_pid_changed.emit(self.process.pid)
            
            self.client_started.emit()
        except Exception as e:
            self.client_error.emit(str(e))

    def _get_linux_terminal(self):
        """Получает подходящий терминал для Linux"""
        terminals = ['gnome-terminal', 'konsole', 'xterm', 'xfce4-terminal', 'mate-terminal', 'lxterminal']
        for terminal in terminals:
            if subprocess.call(['which', terminal], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE) == 0:
                return terminal
        return None

    def stop(self):
        """Остановка клиентского приложения"""
        if self.process and self.process.poll() is None:
            try:
                if sys.platform == "win32":
                    self.process.terminate()
                else:
                    self.process.terminate()
                
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                
                self.process = None
                self.client_stopped.emit()
                
            except Exception as e:
                self.client_error.emit(str(e))

    def force_kill(self):
        """Принудительно завершает процесс клиента"""
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()  
                self.process.wait() 
                self.process = None
                self.client_stopped.emit()
            except ProcessLookupError:
                # Процесс уже завершен
                self.process = None
                self.client_stopped.emit()
            except Exception as e:
                # Ошибки при завершении процесса
                self.client_error.emit(str(e))

    def get_pid(self):
        """Возвращает PID процесса клиента"""
        if self.process:
            return self.process.pid
        return None

    def is_running(self):
        """Проверка, запущен ли клиент"""
        return self.process and self.process.poll() is None