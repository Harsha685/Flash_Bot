import time
from typing import Optional

import serial

from flashbot.console import console
from flashbot.detector.boards import BoardRegistry
from flashbot.detector.device_id import list_serial_ports

# USB vendors commonly found on development boards and their serial bridges.
DEV_BOARD_VIDS = {"2341", "2a03", "1b4f", "239a", "10c4", "1a86", "0403", "16c0", "0483", "303a", "2e8a"}


class SerialConnection:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None

    def open(self, reset_delay: float = 2.0) -> bool:
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except (serial.SerialException, OSError) as e:
            console.print(f"[err]Could not open {self.port}:[/err] {e}")
            return False
        time.sleep(reset_delay)  # opening the port resets most Arduino-compatible boards
        return True

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def readline(self) -> Optional[str]:
        if not self.is_open():
            return None
        try:
            raw = self._ser.readline()
        except (serial.SerialException, OSError):
            self.close()
            return None
        return raw.decode("utf-8", errors="replace").rstrip("\r\n") if raw else None

    def write(self, data: str) -> bool:
        if not self.is_open():
            return False
        try:
            self._ser.write(data.encode("utf-8"))
            return True
        except (serial.SerialException, OSError):
            return False

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open


def guess_port() -> Optional[str]:
    """Pick the most likely board port: a recognised board, then a known vendor, then anything."""
    ports = list_serial_ports()
    if not ports:
        return None
    registry = BoardRegistry()
    for p in ports:
        if registry.lookup(p.vid, p.pid):
            return p.port
    for p in ports:
        if p.vid in DEV_BOARD_VIDS:
            return p.port
    return ports[0].port
