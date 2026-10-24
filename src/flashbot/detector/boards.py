"""
Board registry: built-in USB IDs, user registrations, and FQBN helpers.

User registrations live in <workspace>/config/user_boards.json and take
precedence over the built-in table, so a generic USB-serial bridge (CP210x,
CH340, FTDI) can be re-mapped to whatever board it is actually attached to.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flashbot.workspace import get_workspace


@dataclass
class BoardInfo:
    name: str
    fqbn: str
    pio_board: Optional[str] = None

    def __post_init__(self):
        if not self.pio_board:
            self.pio_board = FQBN_TO_PIO.get(self.fqbn)


# FQBN -> PlatformIO board ID, used to match PlatformIO environments to a
# detected board. Entries can be overridden per board with "pio_board".
FQBN_TO_PIO = {
    "arduino:avr:uno":                     "uno",
    "arduino:avr:nano":                    "nanoatmega328new",
    "arduino:avr:nano:cpu=atmega328old":   "nanoatmega328",
    "arduino:avr:mega":                    "megaatmega2560",
    "arduino:avr:leonardo":                "leonardo",
    "arduino:avr:micro":                   "micro",
    "arduino:megaavr:nona4809":            "nano_every",
    "arduino:samd:nano_33_iot":            "nano_33_iot",
    "arduino:renesas_uno:unor4wifi":       "uno_r4_wifi",
    "arduino:renesas_uno:minima":          "uno_r4_minima",
    "esp32:esp32:esp32":                   "esp32dev",
    "esp32:esp32:esp32s2":                 "esp32-s2-saola-1",
    "esp32:esp32:esp32s3":                 "esp32-s3-devkitc-1",
    "esp32:esp32:esp32c3":                 "esp32-c3-devkitm-1",
    "rp2040:rp2040:rpipico":               "pico",
    "rp2040:rp2040:rpipicow":              "rpipicow",
    "teensy:avr:teensy40":                 "teensy40",
    "teensy:avr:teensy41":                 "teensy41",
    "STMicroelectronics:stm32:Nucleo_64:pnum=NUCLEO_F401RE": "nucleo_f401re",
    "STMicroelectronics:stm32:Nucleo_64:pnum=NUCLEO_F446RE": "nucleo_f446re",
    "STMicroelectronics:stm32:GenF1:pnum=BLUEPILL_F103C8":   "bluepill_f103c8",
}

# Boards that can be identified from their USB VID:PID alone.
BUILTIN_BOARDS: dict[tuple[str, str], BoardInfo] = {
    ("2341", "0043"): BoardInfo("Arduino Uno", "arduino:avr:uno"),
    ("2341", "0001"): BoardInfo("Arduino Uno", "arduino:avr:uno"),
    ("2a03", "0043"): BoardInfo("Arduino Uno", "arduino:avr:uno"),
    ("2341", "0010"): BoardInfo("Arduino Mega 2560", "arduino:avr:mega"),
    ("2341", "0042"): BoardInfo("Arduino Mega 2560", "arduino:avr:mega"),
    ("2341", "8036"): BoardInfo("Arduino Leonardo", "arduino:avr:leonardo"),
    ("2341", "8037"): BoardInfo("Arduino Micro", "arduino:avr:micro"),
    ("2341", "0058"): BoardInfo("Arduino Nano Every", "arduino:megaavr:nona4809"),
    ("2341", "8057"): BoardInfo("Arduino Nano 33 IoT", "arduino:samd:nano_33_iot"),
    ("2341", "1002"): BoardInfo("Arduino Uno R4 WiFi", "arduino:renesas_uno:unor4wifi"),
    ("2341", "0069"): BoardInfo("Arduino Uno R4 Minima", "arduino:renesas_uno:minima"),
    ("10c4", "ea60"): BoardInfo("ESP32 DevKit (CP210x)", "esp32:esp32:esp32"),
    ("1a86", "7523"): BoardInfo("ESP32 (CH340)", "esp32:esp32:esp32"),
    ("303a", "0002"): BoardInfo("ESP32-S2 (native USB)", "esp32:esp32:esp32s2"),
    ("303a", "1001"): BoardInfo("ESP32-C3 (USB-Serial/JTAG)", "esp32:esp32:esp32c3"),
    ("303a", "1002"): BoardInfo("ESP32-S3", "esp32:esp32:esp32s3"),
    ("303a", "1003"): BoardInfo("ESP32-C3", "esp32:esp32:esp32c3"),
    ("2e8a", "000a"): BoardInfo("Raspberry Pi Pico", "rp2040:rp2040:rpipico"),
    ("2e8a", "f00a"): BoardInfo("Raspberry Pi Pico W", "rp2040:rp2040:rpipicow"),
}

# Choices offered when registering an unknown board, grouped by family.
COMMON_BOARDS: dict[str, list[tuple[str, str]]] = {
    "Arduino": [
        ("Arduino Uno", "arduino:avr:uno"),
        ("Arduino Uno R4 WiFi", "arduino:renesas_uno:unor4wifi"),
        ("Arduino Uno R4 Minima", "arduino:renesas_uno:minima"),
        ("Arduino Nano (new bootloader)", "arduino:avr:nano"),
        ("Arduino Nano (old bootloader)", "arduino:avr:nano:cpu=atmega328old"),
        ("Arduino Nano Every", "arduino:megaavr:nona4809"),
        ("Arduino Nano 33 IoT", "arduino:samd:nano_33_iot"),
        ("Arduino Mega 2560", "arduino:avr:mega"),
        ("Arduino Leonardo", "arduino:avr:leonardo"),
    ],
    "Espressif": [
        ("ESP32 Dev Module", "esp32:esp32:esp32"),
        ("ESP32-S2", "esp32:esp32:esp32s2"),
        ("ESP32-S3", "esp32:esp32:esp32s3"),
        ("ESP32-C3", "esp32:esp32:esp32c3"),
    ],
    "Raspberry Pi": [
        ("Raspberry Pi Pico", "rp2040:rp2040:rpipico"),
        ("Raspberry Pi Pico W", "rp2040:rp2040:rpipicow"),
        ("Raspberry Pi Pico 2", "rp2040:rp2040:rpipico2"),
    ],
    "PJRC": [
        ("Teensy 4.0", "teensy:avr:teensy40"),
        ("Teensy 4.1", "teensy:avr:teensy41"),
    ],
    "STMicroelectronics": [
        ("STM32 Nucleo-F401RE", "STMicroelectronics:stm32:Nucleo_64:pnum=NUCLEO_F401RE"),
        ("STM32 Nucleo-F446RE", "STMicroelectronics:stm32:Nucleo_64:pnum=NUCLEO_F446RE"),
        ("STM32 Blue Pill (F103C8)", "STMicroelectronics:stm32:GenF1:pnum=BLUEPILL_F103C8"),
    ],
}


def fqbn_platform(fqbn: str) -> str:
    """'esp32:esp32:esp32s3' -> 'esp32:esp32' (the arduino-cli core ID)."""
    return ":".join(fqbn.split(":")[:2])


def is_valid_fqbn(fqbn: str) -> bool:
    parts = fqbn.split(":")
    return len(parts) in (3, 4) and all(parts)


def _key(vid: str, pid: str) -> str:
    return f"{vid.lower()}:{pid.lower()}"


class BoardRegistry:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else get_workspace().user_boards_path
        self.user: dict[tuple[str, str], BoardInfo] = {}
        self.load()

    def load(self) -> None:
        self.user = {}
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        for key, info in data.items():
            try:
                vid, pid = key.lower().split(":")
                self.user[(vid, pid)] = BoardInfo(
                    name=info["name"], fqbn=info["fqbn"], pio_board=info.get("pio_board"),
                )
            except (ValueError, KeyError, TypeError):
                continue

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for (vid, pid), info in sorted(self.user.items()):
            entry = {"name": info.name, "fqbn": info.fqbn}
            if info.pio_board and info.pio_board != FQBN_TO_PIO.get(info.fqbn):
                entry["pio_board"] = info.pio_board
            data[_key(vid, pid)] = entry
        self.path.write_text(json.dumps(data, indent=2) + "\n")

    def lookup(self, vid: str, pid: str) -> Optional[BoardInfo]:
        key = (vid.lower(), pid.lower())
        return self.user.get(key) or BUILTIN_BOARDS.get(key)

    def register(self, vid: str, pid: str, info: BoardInfo) -> None:
        self.user[(vid.lower(), pid.lower())] = info
        self.save()

    def remove(self, vid: str, pid: str) -> bool:
        removed = self.user.pop((vid.lower(), pid.lower()), None) is not None
        if removed:
            self.save()
        return removed

    def entries(self) -> list[tuple[str, str, BoardInfo, str]]:
        """All known boards as (vid, pid, info, source); user entries shadow built-ins."""
        rows = {k: (v, "built-in") for k, v in BUILTIN_BOARDS.items()}
        rows.update({k: (v, "user") for k, v in self.user.items()})
        return [(vid, pid, info, src) for (vid, pid), (info, src) in sorted(rows.items())]
