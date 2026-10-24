"""
Terminal serial plotter.

Accepts either labelled values ("temp: 24.5, hum=60") or bare numbers separated
by commas, tabs, or spaces ("24.5,60.2"). Bare columns are named from --labels
or Ch0, Ch1, ... in order.
"""

import re
import signal
import time
from collections import deque
from typing import Optional

from rich import box
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from flashbot.console import console
from flashbot.tools.serial_base import SerialConnection

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_LABELLED = re.compile(rf"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*({_NUMBER})")
_SPLIT = re.compile(r"[,\t ]+")
_BLOCKS = " ▁▂▃▄▅▆▇█"
_COLORS = ["cyan", "magenta", "green", "yellow", "blue", "red"]


def parse_line(line: str, labels: Optional[list[str]] = None) -> dict[str, float]:
    labels = labels or []
    labelled = _LABELLED.findall(line)
    if labelled:
        return {name: float(value) for name, value in labelled}
    fields = [f for f in _SPLIT.split(line.strip()) if f]
    try:
        values = [float(f) for f in fields]
    except ValueError:
        return {}
    return {(labels[i] if i < len(labels) else f"Ch{i}"): v for i, v in enumerate(values)}


def sparkline(values: list[float], lo: float, hi: float) -> str:
    span = (hi - lo) or 1.0
    top = len(_BLOCKS) - 1
    return "".join(_BLOCKS[round((v - lo) / span * top)] for v in values)


class SerialPlotter:
    def __init__(self, port: str, baudrate: int = 115200, history: int = 80,
                 labels: Optional[list[str]] = None):
        self.conn = SerialConnection(port, baudrate)
        self.history = history
        self.labels = labels or []
        self.data: dict[str, deque[float]] = {}
        self._running = False

    def _ingest(self, line: str) -> None:
        for label, value in parse_line(line, self.labels).items():
            self.data.setdefault(label, deque(maxlen=self.history)).append(value)

    def _render(self) -> Panel:
        title = f"Serial Plotter  {self.conn.port} at {self.conn.baudrate} baud"
        if not self.data:
            body = Text("Waiting for numeric data. Expected formats: 'temp: 24.5' or '24.5,60.2'.", style="dim")
            return Panel(body, title=title, border_style="cyan", title_align="left")

        table = Table(box=box.SIMPLE, show_edge=False, pad_edge=False, expand=True)
        table.add_column("Series", no_wrap=True)
        table.add_column("Trend", ratio=1, no_wrap=True, overflow="crop")
        for col in ("Last", "Min", "Max"):
            table.add_column(col, justify="right", no_wrap=True)

        for i, (label, series) in enumerate(self.data.items()):
            values = list(series)
            lo, hi = min(values), max(values)
            color = _COLORS[i % len(_COLORS)]
            table.add_row(
                Text(label, style=f"bold {color}"), Text(sparkline(values, lo, hi), style=color),
                f"{values[-1]:.2f}", f"{lo:.2f}", f"{hi:.2f}",
            )
        footer = Text("Each trend is scaled to its own min and max. Press Ctrl+C to exit.", style="dim")
        return Panel(_stack(table, footer), title=title, border_style="cyan", title_align="left")

    def run(self) -> None:
        if not self.conn.open():
            return
        self._running = True
        previous = signal.signal(signal.SIGINT, lambda *_: setattr(self, "_running", False))
        try:
            with Live(self._render(), console=console, refresh_per_second=10, transient=False) as live:
                while self._running and self.conn.is_open():
                    line = self.conn.readline()
                    if line:
                        self._ingest(line)
                        live.update(self._render())
                    else:
                        time.sleep(0.01)
        finally:
            signal.signal(signal.SIGINT, previous)
            self.conn.close()
            console.print("[muted]Plotter closed.[/muted]")


def _stack(*renderables) -> Table:
    grid = Table.grid()
    for r in renderables:
        grid.add_row(r)
    return grid
