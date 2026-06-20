"""
Watches sketches/ for changes and regenerates the manifest automatically.
No more restarting FlashBot every time you add a sketch.
"""
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flashbot.config.sketch_scanner import update_manifest, SKETCHES_DIR


class _ManifestHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds: float = 1.0):
        self.debounce_seconds = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()

    def _trigger(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, update_manifest)
            self._timer.daemon = True
            self._timer.start()

    def on_created(self, event):
        if event.src_path.endswith(".ino"):
            self._trigger()

    def on_deleted(self, event):
        if event.src_path.endswith(".ino"):
            self._trigger()

    def on_moved(self, event):
        if event.src_path.endswith(".ino") or event.dest_path.endswith(".ino"):
            self._trigger()


def start_sketch_watcher():
    handler = _ManifestHandler()
    observer = Observer()
    observer.schedule(handler, SKETCHES_DIR, recursive=True)
    observer.start()
    return observer