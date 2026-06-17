import serial
import serial.tools.list_ports
import time
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class PortInfo:
    port: str
    vid: str
    pid: str
    serial_number: str
    description: str

class SerialConnection:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._callbacks: list[Callable[[str], None]] = []
    
    def add_callback(self, fn: Callable[[str], None]):
        self._callbacks.append(fn)
    
    def open(self) -> bool:
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Arduino bootloader reset
            return True
        except serial.SerialException as e:
            print(f"Failed to open {self.port}: {e}")
            return False
    
    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None
    
    def readline(self) -> Optional[str]:
        if not self._ser or not self._ser.is_open:
            return None
        try:
            raw = self._ser.readline()
            if raw:
                line = raw.decode('utf-8', errors='replace').strip()
                for cb in self._callbacks:
                    cb(line)
                return line
        except serial.SerialException:
            pass
        return None
    
    def write(self, data: str) -> bool:
        if not self._ser or not self._ser.is_open:
            return False
        try:
            self._ser.write(data.encode('utf-8'))
            return True
        except serial.SerialException:
            return False
    
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    @staticmethod
    def list_ports() -> list[PortInfo]:
        return [
            PortInfo(
                p.device,
                f"{p.vid:04x}" if p.vid else "0000",
                f"{p.pid:04x}" if p.pid else "0000",
                p.serial_number or "",
                p.description or ""
            )
            for p in serial.tools.list_ports.comports()
        ]

def guess_port() -> Optional[str]:
    """Return the most likely Arduino port."""
    ports = SerialConnection.list_ports()
    arduino_vids = {"2341", "2a03", "1b4f", "239a", "10c4", "1a86", "16c0", "0483"}
    for p in ports:
        if p.vid in arduino_vids:
            return p.port
    return ports[0].port if ports else None