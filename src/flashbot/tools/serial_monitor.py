import argparse
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

try:
    from tools.serial_base import SerialConnection, guess_port
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.serial_base import SerialConnection, guess_port

try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class SerialMonitor:
    def __init__(self, port: str, baudrate: int = 115200, log_file: str = None):
        self.conn = SerialConnection(port, baudrate)
        self.log_file = log_file
        self.console = Console() if RICH_AVAILABLE else None
        self._running = False

        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    def _log(self, line: str):
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} | {line}\n")

    def _print(self, line: str, style: str = None):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if self.console:
            if style:
                self.console.print(f"[{timestamp}] ", style="dim", end="")
                self.console.print(line, style=style)
            else:
                self.console.print(f"[{timestamp}] {line}")
        else:
            print(f"[{timestamp}] {line}")
        self._log(line)

    def run(self):
        if not self.conn.open():
            return

        self._running = True

        if self.console:
            self.console.print(Panel.fit(
                f"Serial Monitor\n{self.conn.port} @ {self.conn.baudrate} baud\n"
                "Press Ctrl+C to exit | Type to send",
                title="FlashBot", border_style="green"
            ))
        else:
            print(f"Serial Monitor — {self.conn.port} @ {self.conn.baudrate} baud (Ctrl+C to exit)")

        def input_thread():
            while self._running:
                try:
                    cmd = input()
                    if cmd:
                        self.conn.write(cmd + "\n")
                        self._print(f"→ {cmd}", "yellow")
                except EOFError:
                    break

        t = threading.Thread(target=input_thread, daemon=True)
        t.start()

        try:
            while self._running:
                line = self.conn.readline()
                if line is not None:
                    self._print(line)
                else:
                    time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.conn.close()
            self._print("Disconnected.", "dim")


def main():
    parser = argparse.ArgumentParser(description="FlashBot Serial Monitor")
    parser.add_argument("port", nargs="?", default=None, help="Serial port (auto-detect if omitted)")
    parser.add_argument("-b", "--baud", type=int, default=115200)
    parser.add_argument("-l", "--log", help="Log file path")
    args = parser.parse_args()

    port = args.port or guess_port()
    if not port:
        print("No serial port found. Please specify one.")
        sys.exit(1)

    SerialMonitor(port, args.baud, args.log).run()


if __name__ == "__main__":
    main()