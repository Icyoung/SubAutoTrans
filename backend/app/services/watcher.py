import asyncio
import os
from typing import Callable, Awaitable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
import logging
from . import subtitle as subtitle_service

logger = logging.getLogger(__name__)


def language_tokens(language: str) -> list[str]:
    """Return filename tokens for a target language."""
    base = language.lower().strip()
    tokens = {base}

    if base == "chinese":
        tokens.update([
            "zh",
            "zh-hans",
            "zh-cn",
            "chs",
            "sc",
            "simplified",
            "简",
            "简体",
        ])
    elif base == "english":
        tokens.update(["en", "eng", "english"])
    elif base == "japanese":
        tokens.update(["ja", "jpn", "japanese", "jp"])
    elif base == "korean":
        tokens.update(["ko", "kor", "korean", "kr"])
    elif base == "french":
        tokens.update(["fr", "fra", "fre", "french"])
    elif base == "german":
        tokens.update(["de", "deu", "ger", "german"])
    elif base == "spanish":
        tokens.update(["es", "spa", "spanish"])
    elif base == "russian":
        tokens.update(["ru", "rus", "russian"])
    elif base == "portuguese":
        tokens.update(["pt", "por", "portuguese"])
    elif base == "italian":
        tokens.update(["it", "ita", "italian"])

    tokens.update(tag.lower() for tag in subtitle_service.get_known_language_tags())
    return sorted(tokens)


def has_target_language_marker(name: str, target_language: str) -> bool:
    lower_name = name.lower()
    for token in language_tokens(target_language):
        if not token:
            continue
        t = token.lower()
        if len(t) <= 2:
            patterns = [
                f".{t}.",
                f"_{t}.",
                f"-{t}.",
                f"({t})",
                f"[{t}]",
                f" {t}.",
                f".{t}-",
                f".{t}_",
            ]
            if any(p in lower_name for p in patterns):
                return True
        else:
            if t in lower_name:
                return True
    return False


def is_generated_subtitle(name: str) -> bool:
    """Check if a file appears to be a generated subtitle output."""
    lower_name = name.lower()
    if ".translated." in lower_name:
        return True
    if lower_name.endswith((".srt", ".ass")):
        for tag in subtitle_service.get_known_language_tags():
            if f".{tag.lower()}." in lower_name:
                return True
    return False


def has_matching_subtitle_for_mkv(mkv_path: str, target_language: str) -> bool:
    base = os.path.splitext(os.path.basename(mkv_path))[0]
    directory = os.path.dirname(mkv_path) or "."
    base_lower = base.lower()

    try:
        for name in os.listdir(directory):
            lower_name = name.lower()
            if not lower_name.endswith((".srt", ".ass")):
                continue
            if not lower_name.startswith(base_lower + "."):
                continue
            if has_target_language_marker(name, target_language):
                return True
    except OSError:
        return False

    return False


def should_skip_file(file_path: str, target_language: str) -> bool:
    lower_path = file_path.lower()
    if not lower_path.endswith((".mkv", ".srt", ".ass")):
        return True
    if ".translated." in lower_path:
        return True
    if lower_path.endswith((".srt", ".ass")):
        if is_generated_subtitle(lower_path):
            return True
        if has_target_language_marker(file_path, target_language):
            return True
    if lower_path.endswith(".mkv"):
        if has_matching_subtitle_for_mkv(file_path, target_language):
            return True
    return False


class MKVHandler(FileSystemEventHandler):
    """Handler for MKV file events."""

    def __init__(
        self,
        callback: Callable[[str], None],
        target_language: str,
        llm_provider: str,
    ):
        self.callback = callback
        self.target_language = target_language
        self.llm_provider = llm_provider
        self._processed_files: set[str] = set()

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return

        file_path = event.src_path
        if not file_path.lower().endswith((".mkv", ".srt", ".ass")):
            return

        # Avoid processing same file multiple times
        if file_path in self._processed_files:
            return

        if should_skip_file(file_path, self.target_language):
            return

        self._processed_files.add(file_path)
        logger.info(f"New subtitle file detected: {file_path}")
        self.callback(file_path)


class DirectoryWatcher:
    """Watch directories for new MKV files."""

    def __init__(self):
        self._observers: dict[int, Observer] = {}
        self._handlers: dict[int, MKVHandler] = {}
        self._on_new_file: Optional[
            Callable[[str, str, str], Awaitable[None]]
        ] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_new_file_callback(
        self, callback: Callable[[str, str, str], Awaitable[None]]
    ):
        """Set callback for when new MKV files are detected.

        Args:
            callback: async function(file_path, target_language, llm_provider)
        """
        self._on_new_file = callback
        self._loop = asyncio.get_running_loop()

    def start_watching(
        self,
        watcher_id: int,
        path: str,
        target_language: str,
        llm_provider: str,
    ):
        """Start watching a directory."""
        if watcher_id in self._observers:
            self.stop_watching(watcher_id)

        if not os.path.isdir(path):
            raise ValueError(f"Path is not a directory: {path}")

        def on_file_detected(file_path: str):
            if self._on_new_file:
                # Schedule the async callback on the main event loop
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._on_new_file(
                            file_path, target_language, llm_provider
                        ),
                        self._loop,
                    )
                else:
                    logger.error("Event loop not set; cannot dispatch file event")

        handler = MKVHandler(on_file_detected, target_language, llm_provider)
        observer = Observer()
        observer.schedule(handler, path, recursive=True)
        observer.start()

        self._observers[watcher_id] = observer
        self._handlers[watcher_id] = handler

        logger.info(f"Started watching directory: {path}")

    def stop_watching(self, watcher_id: int):
        """Stop watching a directory."""
        if watcher_id in self._observers:
            self._observers[watcher_id].stop()
            self._observers[watcher_id].join()
            del self._observers[watcher_id]
            del self._handlers[watcher_id]
            logger.info(f"Stopped watching watcher {watcher_id}")

    def stop_all(self):
        """Stop all watchers."""
        for watcher_id in list(self._observers.keys()):
            self.stop_watching(watcher_id)

    async def scan_directory(
        self,
        path: str,
        target_language: str,
        llm_provider: str,
    ) -> dict:
        """
        Scan a directory recursively for existing files and trigger callbacks for each.
        Returns stats about the scan.
        """
        if not os.path.isdir(path):
            logger.warning(f"Cannot scan non-existent directory: {path}")
            return {"scanned": 0, "triggered": 0}

        scanned = 0
        triggered = 0

        # Recursively walk through all subdirectories
        for root, dirs, files in os.walk(path):
            for f in files:
                if not f.lower().endswith((".mkv", ".srt", ".ass")):
                    continue

                file_path = os.path.join(root, f)
                if should_skip_file(file_path, target_language):
                    continue

                scanned += 1

                if self._on_new_file and self._loop:
                    try:
                        await self._on_new_file(file_path, target_language, llm_provider)
                        triggered += 1
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")

        logger.info(
            f"Scanned {path} (recursive): {scanned} files, {triggered} tasks triggered"
        )
        return {"scanned": scanned, "triggered": triggered}


# Global watcher instance
directory_watcher = DirectoryWatcher()
