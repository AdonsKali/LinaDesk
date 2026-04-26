import subprocess
import threading
import tempfile
import os
import time
from typing import Optional, Tuple
from backend.core.schemas import ToolSchemaOut

import sounddevice as sd

# Параметры audio
SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_FORMAT = 's16le'
BYTES_PER_SAMPLE = 2
CHUNK_FRAMES = 4096
CHUNK_BYTES = CHUNK_FRAMES * CHANNELS * BYTES_PER_SAMPLE

FFMPEG_PATH = "ffmpeg"

SEARCH_PREFIXES = {
    "youtube": "ytsearch1:",
    "soundcloud": "scsearch1:",
    "bandcamp": "bcsearch1:",
    "mixcloud": "mcsearch1:",
}

class MusicFinderAndStreamer:
    def __init__(self, ffmpeg_path: str = FFMPEG_PATH, js_runtime: Optional[str] = "node"):
        self.ffmpeg_path = ffmpeg_path
        self.js_runtime = js_runtime  # "node", "deno", "bun" or None
        self._play_thread: Optional[threading.Thread] = None
        self._producer_proc = None  # yt-dlp process
        self._ffmpeg_proc = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._playing_lock = threading.Lock()
        self._temp_file = None
        self._current_title = None
        self._current_url = None

    def _run_yt_dlp_get_url(self, query: str, source: str) -> Optional[Tuple[str, str]]:
        """
        Попробовать получить прямую URL-строку (и заголовок) через yt-dlp -j (json) или -g.
        Вернёт (url, title) или None.
        """
        prefix = SEARCH_PREFIXES.get(source)
        if not prefix:
            return None

        search = prefix + query
        cmd = ["yt-dlp"]
        if self.js_runtime:
            cmd += ["--js-runtime", self.js_runtime]
        # Просим JSON с info для лучшего контроля
        cmd += ["-j", "-f", "bestaudio", search]

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if p.returncode != 0 or not p.stdout:
                return None
            import json
            info = json.loads(p.stdout.splitlines()[0])
            # yt-dlp иногда даёт прямой url в поле "url" или в formats
            if "url" in info and info["url"]:
                return info["url"], info.get("title", "")
            # иначе ищем в formats
            fmts = info.get("formats", []) or []
            # Попытаемся предпочесть m4a/aac, затем opus/webm, затем любой bestaudio
            prefer_exts = ["m4a", "webm", "mp3", "m4a"]
            for ext in prefer_exts:
                for f in fmts[::-1]:
                    if f.get("ext") == ext and f.get("url"):
                        return f["url"], info.get("title", "")
            # fallback: первый доступный format с url
            for f in fmts[::-1]:
                if f.get("url"):
                    return f["url"], info.get("title", "")
            return None
        except Exception:
            return None

    def universal_search(self, query: str) -> Optional[Tuple[str, str, str]]:
        """
        Ищем по источникам в порядке: youtube, soundcloud, bandcamp, mixcloud.
        Возвращаем (url, title, source) или None.
        """
        for src in ["youtube", "soundcloud", "bandcamp", "mixcloud"]:
            print(f"[search] Trying {src} ...")
            res = self._run_yt_dlp_get_url(query, src)
            if res:
                url, title = res
                print(f"[search] Found on {src}: {title or url}")
                return url, title or "", src
        return None

    def _stream_via_pipe(self, source_spec: str) -> bool:
        """
        Попытка запустить pipeline: yt-dlp -> ffmpeg(pipe) -> stdout (PCM) -> sounddevice.
        source_spec может быть либо "search:<query>" либо прямой URL.
        Возвращает True, если стартовало воспроизведение (в фоне).
        """
        # Останавливаем предыдущие воспроизведения
        self.stop()

        # Формируем команду yt-dlp (если source_spec начинается с "search:" - используем поиск)
        if source_spec.startswith("search:"):
            query = source_spec.split(":", 1)[1]
            # yt-dlp будет писать в stdout декодированный медиа-поток (raw file)
            ytdlp_cmd = ["yt-dlp", "-f", "bestaudio", "-o", "-", f"ytsearch1:{query}"]
            if self.js_runtime:
                ytdlp_cmd.insert(1, "--js-runtime")
                ytdlp_cmd.insert(2, self.js_runtime)
        else:
            # передан прямой URL — можно запустить ffmpeg напрямую
            ytdlp_cmd = None

        # ffmpeg команда - читать из stdin (pipe:0) если есть yt-dlp, иначе из URL
        if ytdlp_cmd:
            ff_in = "pipe:0"
        else:
            ff_in = source_spec

        ffmpeg_cmd = [
            self.ffmpeg_path,
            "-hide_banner", "-loglevel", "error",
            "-i", ff_in,
            "-vn",
            "-f", SAMPLE_FORMAT,
            "-ac", str(CHANNELS),
            "-ar", str(SAMPLE_RATE),
            "pipe:1"
        ]

        try:
            if ytdlp_cmd:
                self._producer_proc = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self._ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=self._producer_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=CHUNK_BYTES)
            else:
                self._producer_proc = None
                self._ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=CHUNK_BYTES)

            self._stop_event.clear()
            self._pause_event.set() 
            self._play_thread = threading.Thread(target=self._reader_thread, args=(self._ffmpeg_proc.stdout,))
            self._play_thread.daemon = True
            self._play_thread.start()
            return True
        except Exception as e:
            print("[stream] start failed:", e)
            self.stop()
            return False

    def _reader_thread(self, stdout_pipe):
        """
        Читает байты от ffmpeg stdout и пишет в sounddevice stream, с поддержкой pause/stop.
        """
        try:
            stream = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK_FRAMES)
            stream.start()
        except Exception as e:
            print("[audio] Failed to open output stream:", e)
            self.stop()
            return

        try:
            while not self._stop_event.is_set():
                if not self._pause_event.is_set():
                    time.sleep(0.05)
                    continue

                data = stdout_pipe.read(CHUNK_BYTES)
                # if not data:
                #     break
                try:
                    stream.write(data)
                except Exception as e:
                    print("[audio] write error:", e)
                    break
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                pass
            # ensure subprocesses are cleaned
                print(f"error: {e}")
            self.stop()

    def _download_to_temp_and_play(self, source_spec: str):
        """
        Фоллбек: скачиваем трек во временный файл и воспроизводим локально через ffmpeg -> sounddevice.
        Возвращаем True при успехе.
        """
        # определим путь temp
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tmp.close()
        out_path = tmp.name
        try:
            if source_spec.startswith("search:"):
                query = source_spec.split(":", 1)[1]
                cmd = ["yt-dlp", "-f", "bestaudio", "-o", out_path, f"ytsearch1:{query}"]
            else:
                cmd = ["yt-dlp", "-f", "bestaudio", "-o", out_path, source_spec]
            if self.js_runtime:
                cmd.insert(1, "--js-runtime")
                cmd.insert(2, self.js_runtime)
            print("[download] running:", " ".join(cmd))
            res = subprocess.run(cmd)
            if res.returncode != 0:
                print("[download] yt-dlp failed")
                try:
                    os.unlink(out_path)
                except Exception:
                    pass
                return ToolSchemaOut(
                    status='error',
                )
            # запустим ffmpeg на файл
            ok = self._stream_via_pipe(out_path)
            if ok:
                self._temp_file = out_path
                return ToolSchemaOut(
                    status='ok',
                )
            else:
                try:
                    os.unlink(out_path)
                except Exception:
                    pass
                return False
        except Exception as e:
            print("[download] failed:", e)
            try:
                os.unlink(out_path)
            except Exception:
                pass
            return False

    ### Публичные методы ###
    def play_search(self, query: str):
        """
        Попробовать воспроизвести по поисковому запросу (универсально).
        """
        # Сначала попробуем получить прямой url через universal_search
        res = self.universal_search(query)
        if res:
            url, title, src = res
            self._current_title = title
            self._current_url = url
            # Попробуем стримить прямой URL через ffmpeg
            print(f"[play] trying direct url from {src}: {title}")
            ok = self._stream_via_pipe(url)
            if ok:
                return ToolSchemaOut(
                    status='ok',
                )
            # если failed, попробуем через yt-dlp pipe: yt-dlp -> ffmpeg
            print("[play] direct url failed, trying yt-dlp -> ffmpeg pipe...")
            ok2 = self._stream_via_pipe(f"search:{query}")  # yt-dlp mode
            if ok2:
                return ToolSchemaOut(
                    status='ok',
                )
            # fallback: скачиваем в файл и проигрываем
            print("[play] pipe failed, fallback: downloading to temp file...")
            return self._download_to_temp_and_play(query)
        else:
            # Не найдено прямого url — попробуем напрямую yt-dlp pipe и fallback
            print("[play] nothing found via direct search, trying yt-dlp pipe directly.")
            ok_pipe = self._stream_via_pipe(f"search:{query}")
            if ok_pipe:
                return ToolSchemaOut(
                    status='ok',
                )
            return self._download_to_temp_and_play(query)

    def play_url(self, url: str):
        """
        Воспроизвести прямой URL (или скачать/stream fallback).
        """
        self._current_url = url
        # попробуем идти через ffmpeg -> stdout
        ok = self._stream_via_pipe(url)
        if ok:
            return ToolSchemaOut(
                status='ok',
            )
        # иначе попробуем yt-dlp pipe mode (download via yt-dlp then pipe)
        ok2 = self._stream_via_pipe(f"search:{url}")
        if ok2:
            return ToolSchemaOut(
                status='ok',
            )
        return self._download_to_temp_and_play(url)

    def pause(self):
        """Поставить на паузу (streaming будет удерживаться)."""
        print("[control] pause")
        self._pause_event.clear()

    def resume(self):
        """Возобновить."""
        print("[control] resume")
        self._pause_event.set()

    def stop(self):
        """Остановить и очистить ресурсы."""
        print("[control] stop")
        self._stop_event.set()
        self._pause_event.set()
        try:
            if self._ffmpeg_proc and self._ffmpeg_proc.poll() is None:
                self._ffmpeg_proc.kill()
        except Exception:
            pass
        try:
            if self._producer_proc and self._producer_proc.poll() is None:
                self._producer_proc.kill()
        except Exception:
            pass
        self._ffmpeg_proc = None
        self._producer_proc = None
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception:
                pass
            self._temp_file = None

    def current_info(self):
        return {"title": self._current_title, "url": self._current_url}