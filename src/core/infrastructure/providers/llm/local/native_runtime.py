"""Discover optional NVIDIA wheel DLLs inside the active Python environment."""
import ctypes
import os
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

_directories = {}
_libraries = {}


def register_runtime_directories():
    if os.name != "nt":
        return
    for name in ("nvidia-cublas", "nvidia-cuda-runtime", "nvidia-cuda-nvrtc"):
        try:
            package = distribution(name)
        except PackageNotFoundError:
            continue
        for file in package.files or ():
            if str(file).lower().endswith(".dll"):
                folder = str(Path(package.locate_file(file)).resolve().parent)
                if folder not in _directories:
                    _directories[folder] = os.add_dll_directory(folder)
                    # Native ggml also uses the process DLL search path.
                    os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")


def verify_cuda_library(module):
    if os.name != "nt" or not getattr(module, "__file__", None):
        return
    library = Path(module.__file__).parent / "lib" / "ggml-cuda.dll"
    if library.is_file() and str(library) not in _libraries:
        try:
            _libraries[str(library)] = ctypes.WinDLL(str(library))
        except OSError as exc:
            raise RuntimeError(
                "Не удалось загрузить ggml-cuda.dll или её зависимости CUDA/cuBLAS. "
                "Проверьте CUDA Runtime в окружении Python."
            ) from exc
