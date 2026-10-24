"""Identify connected serial devices and track them across USB re-enumeration."""

import time
from dataclasses import dataclass
from typing import Optional, Union

import serial.tools.list_ports

from flashbot.detector.boards import BoardRegistry

# Intel host controllers and similar on-board devices that expose tty nodes.
IGNORED_VIDS = {"8086"}


def device_key(serial_number: str, vid: str, pid: str, port: str) -> str:
    """
    Stable identity for a physical board. The USB serial number survives resets
    and port changes; boards without one (most CH340 and some FTDI bridges) keep
    their tty path across resets instead, so the port tells two of them apart.
    """
    return serial_number or f"{vid}:{pid}@{port}"


@dataclass
class PortInfo:
    port: str
    vid: str
    pid: str
    serial_number: str = ""
    description: str = ""

    @property
    def key(self) -> str:
        return device_key(self.serial_number, self.vid, self.pid, self.port)


@dataclass
class DetectedDevice:
    port: str
    name: str
    fqbn: str
    vid: str
    pid: str
    serial_number: str = ""
    pio_board: Optional[str] = None

    @property
    def key(self) -> str:
        return device_key(self.serial_number, self.vid, self.pid, self.port)


@dataclass
class UnknownBoard:
    port: str
    vid: str
    pid: str
    serial_number: str = ""
    description: str = ""

    @property
    def key(self) -> str:
        return device_key(self.serial_number, self.vid, self.pid, self.port)


Identified = Union[DetectedDevice, UnknownBoard]


def identify(info: PortInfo, registry: Optional[BoardRegistry] = None) -> Optional[Identified]:
    if not info.vid or not info.pid or info.vid in IGNORED_VIDS:
        return None
    registry = registry or BoardRegistry()
    board = registry.lookup(info.vid, info.pid)
    if board:
        return DetectedDevice(
            port=info.port, name=board.name, fqbn=board.fqbn,
            vid=info.vid, pid=info.pid, serial_number=info.serial_number,
            pio_board=board.pio_board,
        )
    return UnknownBoard(
        port=info.port, vid=info.vid, pid=info.pid,
        serial_number=info.serial_number, description=info.description,
    )


def port_info_from_udev(udev_device) -> Optional[PortInfo]:
    vid = (udev_device.get("ID_VENDOR_ID") or "").lower()
    pid = (udev_device.get("ID_MODEL_ID") or "").lower()
    port = udev_device.get("DEVNAME") or ""
    if not (vid and pid and port):
        return None
    return PortInfo(
        port=port, vid=vid, pid=pid,
        serial_number=udev_device.get("ID_SERIAL_SHORT") or "",
        description=udev_device.get("ID_MODEL_FROM_DATABASE") or udev_device.get("ID_MODEL") or "",
    )


def list_serial_ports() -> list[PortInfo]:
    """USB serial ports currently present (ports without a USB VID are skipped)."""
    return [
        PortInfo(
            port=p.device,
            vid=f"{p.vid:04x}",
            pid=f"{p.pid:04x}",
            serial_number=p.serial_number or "",
            description=p.description or "",
        )
        for p in serial.tools.list_ports.comports()
        if p.vid is not None
    ]


def find_port(port: str) -> Optional[PortInfo]:
    return next((p for p in list_serial_ports() if p.port == port), None)


def connected_devices(registry: Optional[BoardRegistry] = None) -> list[Identified]:
    registry = registry or BoardRegistry()
    found = (identify(p, registry) for p in list_serial_ports())
    return [d for d in found if d is not None]


def wait_for_port(device: DetectedDevice, timeout: float = 12.0, settle: float = 1.0) -> Optional[str]:
    """
    Wait for a board to reappear after upload and return its current port.

    Boards with native USB (Uno R4, Leonardo, Pico, ESP32-C3/S3) drop off the
    bus while resetting and may come back on a different tty path.
    """
    time.sleep(settle)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        candidates = [
            p for p in list_serial_ports()
            if (device.serial_number and p.serial_number == device.serial_number)
            or (not device.serial_number and p.vid == device.vid and p.pid == device.pid)
        ]
        if candidates:
            same = [p for p in candidates if p.port == device.port]
            return (same or candidates)[0].port
        time.sleep(0.25)
    return None
