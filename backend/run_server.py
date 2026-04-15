import sys
import subprocess
import locale

def main():
    host = "127.0.0.1"
    port = "8000"
    debug = "--reload" if len(sys.argv) > 1 and sys.argv[1] == "--debug" else ""
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.run:create_application",
        "--host", host,
        "--port", port,
        "--log-level", "debug" if debug else "info",
    ]
    
    if debug:
        cmd.append("--reload")
    
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
        


if __name__ == "__main__":
    main()