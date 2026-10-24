"""Interactive serial monitor: prints timestamped device output and sends typed lines."""

import select
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.text import Text

from flashbot.console import console
from flashbot.tools.serial_base import SerialConnection


class SerialMonitor:
    def __init__(self, port: str, baudrate: int = 115200, log_file: Optional[str] = None):
        self.conn = SerialConnection(port, baudrate)
        self.log_file = Path(log_file) if log_file else None
        self._running = False
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _emit(self, line: str, style: str = "") -> None:
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # Device output is printed as plain Text so brackets are never parsed as Rich markup.
        console.print(Text.assemble((f"{stamp}  ", "dim"), (line, style)), highlight=False)
        if self.log_file:
            with self.log_file.open("a") as f:
                f.write(f"{datetime.now().isoformat()} | {line}\n")

    def _read_stdin(self, stop: threading.Event) -> None:
        while not stop.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.2)
            if not ready:
                continue
            cmd = sys.stdin.readline()
            if not cmd:  # stdin closed
                return
            cmd = cmd.rstrip("\n")
            if cmd:
                self.conn.write(cmd + "\n")
                self._emit(f"> {cmd}", "yellow")

    def run(self) -> None:
        if not self.conn.open():
            return

        self._running = True
        previous = signal.signal(signal.SIGINT, lambda *_: setattr(self, "_running", False))
        console.print(Panel.fit(
            f"[bold]Serial Monitor[/bold]  {self.conn.port} at {self.conn.baudrate} baud\n"
            "[muted]Type a line and press Enter to send. Press Ctrl+C to exit.[/muted]",
            border_style="cyan",
        ))

        stop = threading.Event()
        reader = threading.Thread(target=self._read_stdin, args=(stop,), daemon=True)
        reader.start()
        try:
            while self._running:
                if not self.conn.is_open():
                    self._emit("Connection lost.", "red")
                    break
                line = self.conn.readline()
                if line is None:
                    time.sleep(0.01)
                elif line:
                    self._emit(line)
        finally:
            stop.set()
            reader.join(timeout=1)
            signal.signal(signal.SIGINT, previous)
            self.conn.close()
            console.print("[muted]Monitor closed.[/muted]")
