from PySide6.QtCore import QObject, Signal
import subprocess
import sys
import os
import time
import threading
from typing import Optional, List
from enum import Enum
from launcher.model.launcher_model import ProcessInfo
from utils.logger import logger

log = logger.get(__name__)

class ProcessType(Enum):
    SERVER = "server"
    CLIENT = "client"


class ProcessManager(QObject):
    """Manages external processes (server and client) for the application"""
    
    process_started = Signal(ProcessType)
    process_stopped = Signal(ProcessType)
    process_error = Signal(ProcessType, str)
    process_pid_changed = Signal(ProcessType, int)
    
    def __init__(self):
        super().__init__()
        self._processes = {
            ProcessType.SERVER: ProcessInfo(process=None, identifier="run_server.py"),
            ProcessType.CLIENT: ProcessInfo(process=None, identifier="client/main.py")
        }
        self.debug_mode = False
        self.host = "127.0.0.1"
        self.port = "8000"
        self._server_health_timeout = 5000
    
    # Public API
    def start_server(self) -> bool:
        """Start the server process. Returns True if successful."""
        return self._start_process(ProcessType.SERVER, self._get_server_command())
    
    def start_client(self, language: str = 'en') -> bool:
        """Start the client process. Returns True if successful."""
        return self._start_process(ProcessType.CLIENT, self._get_client_command(language))
    
    def stop_server(self, force: bool = False) -> None:
        self._stop_process(ProcessType.SERVER, force)
    
    def stop_client(self, force: bool = False) -> None:
        self._stop_process(ProcessType.CLIENT, force)
    
    def stop_all(self, force: bool = False) -> None:
        """Stop both client and server processes"""
        self.stop_client(force)
        self.stop_server(force)
    
    def is_running(self, process_type: ProcessType) -> bool:
        """Check if a specific process is running"""
        return self._processes[process_type].is_running()
    
    def get_pid(self, process_type: ProcessType) -> int:
        """Get PID of a process or -1 if not running"""
        info = self._processes[process_type]
        if info.is_running() and info.process:
            return info.process.pid
        return -1
    
    def cleanup_hanging_processes(self, saved_pids: dict) -> None:
        """
        Terminate hanging processes from previous sessions
        saved_pids: dict with 'server' and 'client' keys containing PIDs
        """
        for proc_type_str, pid in saved_pids.items():
            try:
                proc_type = ProcessType(proc_type_str)
                self._terminate_process_by_pid(pid, proc_type.value.isidentifier()) #type: ignore
            except ValueError:
                continue
    
    # Private methods
    def _start_process(self, proc_type: ProcessType, cmd: List[str]) -> bool:
        """Generic method to start a process"""
        if self.is_running(proc_type):
            self.process_error.emit(proc_type, f"{proc_type.value} is already running")
            return False
        
        def run():
            try:
                process = self._create_process(cmd)
                if not process:
                    self.process_error.emit(proc_type, f"Failed to create {proc_type.value} process")
                    return
                
                info = self._processes[proc_type]
                info.process = process
                
                # Wait for server to be ready if needed
                if proc_type == ProcessType.SERVER:
                    if not self._wait_for_server():
                        self.process_error.emit(proc_type, "Server didn't respond to health check")
                        self._stop_process(proc_type, force=True)
                        return
                
                self.process_started.emit(proc_type)
                self.process_pid_changed.emit(proc_type, process.pid)
                
            except Exception as e:
                self.process_error.emit(proc_type, f"Startup error: {str(e)}")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True
    
    def _stop_process(self, proc_type: ProcessType, force: bool = False) -> None:
        """Generic method to stop a process"""
        info = self._processes[proc_type]
        
        if not info.is_running():
            return
        
        try:
            if force:
                info.process.kill() #type: ignore
            else:
                info.process.terminate() #type: ignore
            
            try:
                info.process.wait(timeout=5 if force else 10) #type: ignore
            except subprocess.TimeoutExpired:
                info.process.kill() #type: ignore
                info.process.wait(timeout=2) #type: ignore
                
        except Exception as e:
            # Log error but continue with cleanup
            print(f"Error stopping {proc_type.value}: {e}")
        finally:
            info.process = None
            self.process_pid_changed.emit(proc_type, -1)
            self.process_stopped.emit(proc_type)
    
    def _create_process(self, cmd: List[str]) -> Optional[subprocess.Popen]:
        """Create a new process with platform-specific handling"""
        try:
            if sys.platform == "win32":
                return subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Linux/Mac
                terminal = self._get_linux_terminal()
                if terminal:
                    full_cmd = " ".join(cmd)
                    return subprocess.Popen([
                        terminal, "-e", "bash", "-c", f"{full_cmd}; exec bash"
                    ])
                else:
                    return subprocess.Popen(
                        cmd,
                        cwd=os.getcwd(),
                        preexec_fn=os.setpgrp if hasattr(os, 'setpgrp') else None
                    )
        except Exception as e:
            self.process_error.emit(
                ProcessType.SERVER if "run_server" in cmd[0] else ProcessType.CLIENT,
                f"Failed to create process: {e}"
            )
            return None
    
    def _get_server_command(self) -> List[str]:
        """Build server command line"""
        cmd = [sys.executable, "-m", "uvicorn",
            "backend.main:create_application",
            "--host", self.host,
            "--port", self.port,]
        if self.debug_mode:
            log.debug("Starting server in debug mode")
            cmd.append("--debug")
        return cmd
    
    def _get_client_command(self, language: str) -> List[str]:
        """Build client command line"""
        cmd = [sys.executable, "client/main.py", "--lang", language]
        if self.debug_mode:
            log.debug("Starting client in debug mode")
            cmd.append("--debug")
        return cmd
    
    def _wait_for_server(self) -> bool:
        """Wait for server to respond to health checks"""
        try:
            import requests
        except ImportError:
            # If requests not available, assume server is running
            return True
        
        start_time = time.time()
        while time.time() - start_time < self._server_health_timeout:
            try:
                response = requests.get(
                    f"http://{self.host}:{self.port}/health",
                    timeout=1
                )
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(0.5)
        
        return False
    
    def _get_linux_terminal(self) -> Optional[str]:
        """Find available terminal emulator on Linux"""
        terminals = ['xterm', 'gnome-terminal', 'konsole', 'xfce4-terminal']
        for terminal in terminals:
            try:
                result = subprocess.run(
                    ['which', terminal],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return terminal
            except:
                continue
        return None
    
    def _terminate_process_by_pid(self, pid: int, expected_cmd_fragment: str) -> None:
        """Terminate a process by PID if it matches expected command"""
        if pid <= -1:
            return
        
        try:
            import psutil
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline()).lower()
            
            if expected_cmd_fragment.lower() in cmdline and proc.is_running():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except ImportError:
            # Fallback to platform-specific commands
            self._terminate_process_fallback(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def _terminate_process_fallback(self, pid: int) -> None:
        """Fallback termination without psutil"""
        if sys.platform == "win32":
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                          capture_output=True, check=False)
        else:
            try:
                os.kill(pid, 15)  # SIGTERM
                time.sleep(0.5)
                os.kill(pid, 9)   # SIGKILL if still alive
            except OSError:
                pass