import re
import time
from typing import Optional

import serial


class SerialComm:
    """Line-oriented serial access for automated tests."""

    def __init__(self, port: str, baud: int = 9600, timeout: float = 0.2):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None

    def connect(self, retries: int = 5, delay: float = 1.0, boot_delay: float = 2.0) -> None:
        """Open the port, retrying while the OS finishes re-enumerating the board."""
        last_error = None
        for attempt in range(retries):
            try:
                self.serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
                time.sleep(boot_delay)  # opening the port resets many boards
                return
            except (serial.SerialException, OSError) as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)
        raise ConnectionError(f"Could not open {self.port} after {retries} attempts: {last_error}")

    def disconnect(self) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()

    def is_connected(self) -> bool:
        return self.serial is not None and self.serial.is_open

    def read_until(self, expect: str, timeout: float, regex: bool = False) -> tuple[bool, list[str]]:
        """Read lines until one contains `expect` (or matches it, if regex) or the timeout expires."""
        if not self.is_connected():
            raise RuntimeError("Serial port is not open")
        pattern = re.compile(expect) if regex else None
        lines: list[str] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.serial.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            lines.append(line)
            if (pattern.search(line) if pattern else expect in line):
                return True, lines
        return False, lines

    def transact(self, command: str, expect: str, timeout: float,
                 regex: bool = False) -> tuple[bool, list[str]]:
        """Send a command and wait for a matching line. Without `expect`, any reply passes."""
        if not self.is_connected():
            raise RuntimeError("Serial port is not open")
        self.serial.reset_input_buffer()
        self.serial.write((command + "\n").encode("utf-8"))
        self.serial.flush()
        if expect:
            return self.read_until(expect, timeout, regex)
        return self.read_until("", timeout)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
