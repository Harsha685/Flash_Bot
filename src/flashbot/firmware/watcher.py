"""Watches sketches/ and regenerates the manifest when firmware is added or removed."""

import threading
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from flashbot.firmware.scanner import ScanResult, update_manifest
from flashbot.workspace import Workspace, get_workspace

WATCHED_NAMES = ("platformio.ini",)
WATCHED_SUFFIXES = (".ino",)


def _relevant(path) -> bool:
    path = str(path)
    return path.endswith(WATCHED_SUFFIXES) or path.endswith(WATCHED_NAMES)


class _ManifestHandler(FileSystemEventHandler):
    def __init__(self, ws: Workspace, on_update: Optional[Callable[[ScanResult], None]],
                 debounce_seconds: float = 1.0):
        self.ws = ws
        self.on_update = on_update
        self.debounce_seconds = debounce_seconds
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _rescan(self):
        result = update_manifest(self.ws)
        if self.on_update:
            self.on_update(result)

    def _trigger(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._rescan)
            self._timer.daemon = True
            self._timer.start()

    def on_any_event(self, event):
        if event.event_type not in ("created", "deleted", "moved"):
            return
        dest = getattr(event, "dest_path", "")
        if event.is_directory or _relevant(event.src_path) or _relevant(dest):
            self._trigger()


def start_sketch_watcher(ws: Optional[Workspace] = None,
                         on_update: Optional[Callable[[ScanResult], None]] = None) -> Observer:
    ws = ws or get_workspace()
    ws.sketches_dir.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(_ManifestHandler(ws, on_update), str(ws.sketches_dir), recursive=True)
    observer.daemon = True
    observer.start()
    return observer
