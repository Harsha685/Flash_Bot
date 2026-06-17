import argparse
import sys
import time
import re
from collections import deque
from pathlib import Path

try:
    from tools.serial_base import SerialConnection, guess_port
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.serial_base import SerialConnection, guess_port

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class SerialPlotter:
    def __init__(self, port: str, baudrate: int = 115200,
                 history: int = 80, labels: list = None):
        self.conn = SerialConnection(port, baudrate)
        self.history = history
        self.labels = labels or []
        self.data: dict[str, deque[float]] = {}
        self.console = Console() if RICH_AVAILABLE else None
        self._running = False
        
    def _parse_line(self, line: str) -> dict[str, float]:
        result = {}
        
        # Format: "Temp: 24.5" or "Temp=24.5"
        labeled = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(-?\d+\.?\d*)', line)
        if labeled:
            for label, val in labeled:
                result[label] = float(val)
            return result
        
        # Format: "24.5,60.2,1023"
        try:
            vals = [float(x.strip()) for x in line.split(',') if x.strip()]
            for i, v in enumerate(vals):
                label = self.labels[i] if i < len(self.labels) else f"Ch{i}"
                result[label] = v
            return result
        except ValueError:
            pass
        
        return {}
    
    def _render_ascii(self, data: dict[str, deque[float]]) -> str:
        lines = []
        max_val = 0.01
        min_val = 0
        
        for series in data.values():
            if series:
                max_val = max(max_val, max(series))
                min_val = min(min_val, min(series))
        
        height = 10
        for label, series in data.items():
            if not series:
                continue
            vals = list(series)
            line = f"{label:12} "
            
            rng = max_val - min_val if max_val != min_val else 1
            bars = []
            for v in vals[-self.history:]:
                h = int(((v - min_val) / rng) * height)
                bars.append(h)
            
            spark = ""
            for h in bars:
                blocks = " ▁▂▃▄▅▆▇█"
                idx = min(h, len(blocks)-1)
                spark += blocks[idx]
            
            line += spark + f"  ({vals[-1]:.2f})"
            lines.append(line)
        
        return "\n".join(lines) if lines else "Waiting for numeric data..."
    
    def _render_rich(self, data: dict[str, deque[float]]):
        content = self._render_ascii(data)
        return Panel(
            Text(content),
            title=f"Serial Plotter — {self.conn.port} @ {self.conn.baudrate}",
            border_style="cyan"
        )
    
    def run(self):
        if not self.conn.open():
            return
        
        self._running = True
        print(f"Serial Plotter — {self.conn.port} @ {self.conn.baudrate}")
        print("Expecting: 'Temp: 24.5' or '24.5,60.2' format. Ctrl+C to exit.\n")
        
        if self.console:
            with Live(self._render_rich(self.data), refresh_per_second=10) as live:
                try:
                    while self._running:
                        line = self.conn.readline()
                        if line:
                            parsed = self._parse_line(line)
                            for label, val in parsed.items():
                                if label not in self.data:
                                    self.data[label] = deque(maxlen=self.history)
                                self.data[label].append(val)
                            live.update(self._render_rich(self.data))
                        else:
                            time.sleep(0.01)
                except KeyboardInterrupt:
                    pass
        else:
            try:
                while self._running:
                    line = self.conn.readline()
                    if line:
                        parsed = self._parse_line(line)
                        for label, val in parsed.items():
                            if label not in self.data:
                                self.data[label] = deque(maxlen=self.history)
                            self.data[label].append(val)
                        print("\033[2J\033[H")
                        print(self._render_ascii(self.data))
                    else:
                        time.sleep(0.05)
            except KeyboardInterrupt:
                pass
        
        self.conn.close()
        print("\nDisconnected.")


def main():
    parser = argparse.ArgumentParser(description="FlashBot Serial Plotter")
    parser.add_argument("port", nargs="?", default=None, help="Serial port (auto-detect if omitted)")
    parser.add_argument("-b", "--baud", type=int, default=115200)
    parser.add_argument("-n", "--history", type=int, default=80)
    parser.add_argument("--labels", nargs="+", default=[],
                       help="Labels for CSV columns (e.g. --labels Temp Humidity)")
    args = parser.parse_args()
    
    port = args.port or guess_port()
    if not port:
        print("No serial port found. Please specify one.")
        sys.exit(1)
    
    SerialPlotter(port, args.baud, args.history, args.labels).run()


if __name__ == "__main__":
    main()