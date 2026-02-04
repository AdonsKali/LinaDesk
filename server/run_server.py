import sys
import os
import subprocess
import signal
import locale

def main():
    host = "127.0.0.1"
    port = "8000"
    debug = "--reload" if len(sys.argv) > 1 and sys.argv[1] == "--debug" else ""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "server.server:app",
        "--host", host,
        "--port", port,
        "--log-level", "debug" if debug else "info",
    ]
    
    if debug:
        cmd.append("--reload")
    
    print("=" * 50)
    print(f"Запуск сервера на http://{host}:{port}")
    print(f"Команда: {' '.join(cmd)}")
    print("=" * 50)
    print()
    
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_CONSOLE
        process = subprocess.Popen(
            cmd,
            creationflags=creation_flags,
            encoding=locale.getpreferredencoding(),
            errors='replace'
        )
    else:
        # На Linux просто запускаем в терминале
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
    # Выводим логи в реальном времени
    def read_output():
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line.rstrip())
        except Exception as e:
            print(f"Ошибка чтения вывода: {e}")
    
    import threading
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()

if __name__ == "__main__":
    main()