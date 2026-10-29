"""Repeat local CPU embedding inference; report RSS drift, not a claim of no leaks."""
import asyncio
import ctypes
import gc
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.infrastructure.providers.embeddings import SentenceTransformerEmbeddings
from local_paths import BASE_DIR


def rss_bytes():
    if os.name != "nt":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "peak_working", "working", "peak_paged", "paged", "peak_nonpaged",
                "nonpaged", "pagefile", "peak_pagefile")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.working


async def main():
    settings = json.loads((BASE_DIR / "data/settings.json").read_text(encoding="utf-8-sig"))
    provider = SentenceTransformerEmbeddings(settings.get("embedding_model_path"))
    try:
        for _ in range(5):
            await provider.embed_query("Лина запоминает важные факты о разговоре")
        gc.collect()
        before = rss_bytes()
        started = time.perf_counter()
        checkpoints = []
        for index in range(50):
            vector = await provider.embed_query(f"Проверка памяти: разговор номер {index % 5}")
            assert len(vector) == 384
            if (index + 1) % 10 == 0:
                gc.collect()
                checkpoints.append(rss_bytes())
        seconds = time.perf_counter() - started
        await provider.close()
        gc.collect()
        print(json.dumps({"iterations": 50, "seconds": round(seconds, 3),
                          "rss_after_warmup": before, "rss_checkpoints": checkpoints,
                          "rss_after_close": rss_bytes(), "model_released": provider._model is None,
                          "executor_released": provider._executor is None}, indent=2))
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
