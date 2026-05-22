import json
import os
from dataclasses import dataclass
from typing import Optional

USER_BOARDS_PATH = "config/user_boards.json"

# Hardcoded known boards
BOARD_TABLE = {
    ("2341", "0043"): {"name": "Arduino Uno",         "fqbn": "arduino:avr:uno"},
    ("2341", "1002"): {"name": "Arduino Uno WiFi R4",  "fqbn": "arduino:renesas_uno:unor4wifi"},
    ("2341", "0010"): {"name": "Arduino Mega",         "fqbn": "arduino:avr:mega"},
    ("2341", "8036"): {"name": "Arduino Leonardo",     "fqbn": "arduino:avr:leonardo"},
    ("2341", "8037"): {"name": "Arduino Micro",        "fqbn": "arduino:avr:micro"},
}

def _load_user_boards():
    """Load user-registered boards from JSON and merge into BOARD_TABLE."""
    if not os.path.isfile(USER_BOARDS_PATH):
        return
    try:
        with open(USER_BOARDS_PATH, "r") as f:
            user_boards = json.load(f)
        for key_str, info in user_boards.items():
            vid, pid = key_str.split(":")
            BOARD_TABLE[(vid, pid)] = info
    except (json.JSONDecodeError, ValueError):
        pass

def _save_user_boards():
    """Write only user-registered boards (not hardcoded ones) to JSON."""
    os.makedirs(os.path.dirname(USER_BOARDS_PATH), exist_ok=True)
    user_boards = {}
    for (vid, pid), info in BOARD_TABLE.items():
        # Skip hardcoded keys
        if (vid, pid) not in {
            ("2341", "0043"), ("2341", "1002"), ("2341", "0010"),
            ("2341", "8036"), ("2341", "8037")
        }:
            user_boards[f"{vid}:{pid}"] = info
    with open(USER_BOARDS_PATH, "w") as f:
        json.dump(user_boards, f, indent=2)

# Load on module import
_load_user_boards()


@dataclass
class DetectedDevice:
    port: str
    name: str
    fqbn: str
    vid: str
    pid: str
    serial_number: str

@dataclass
class UnknownBoard:
    port: str
    vid: str
    pid: str
    serial_number: str


def detect_from_udev(udev_device) -> Optional[DetectedDevice | UnknownBoard]:
    vid    = udev_device.get("ID_VENDOR_ID",   "").lower()
    pid    = udev_device.get("ID_MODEL_ID",    "").lower()
    port   = udev_device.get("DEVNAME",        "")
    serial = udev_device.get("ID_SERIAL_SHORT","")

    if not vid or not pid:
        return None

    board = BOARD_TABLE.get((vid, pid))
    if board:
        return DetectedDevice(
            port=port,
            name=board["name"],
            fqbn=board["fqbn"],
            vid=vid,
            pid=pid,
            serial_number=serial
        )

    return UnknownBoard(port=port, vid=vid, pid=pid, serial_number=serial)


def prompt_for_fqbn(unknown: UnknownBoard) -> Optional[DetectedDevice]:
    print(f"\n[UNKNOWN BOARD] Detected USB device:")
    print(f"  Port: {unknown.port}")
    print(f"  VID:  {unknown.vid}")
    print(f"  PID:  {unknown.pid}")
    print(f"  Serial: {unknown.serial_number or 'N/A'}")

    register = input("Register this board? (y/n): ").strip().lower()
    if register not in ("y", "yes"):
        return None

    name = input("Enter board name (e.g. 'Arduino Nano'): ").strip()
    fqbn = input("Enter FQBN (e.g. 'arduino:avr:nano'): ").strip()

    if not name or not fqbn:
        print("Name and FQBN required. Skipping.")
        return None

    # Add to runtime table and persist
    BOARD_TABLE[(unknown.vid, unknown.pid)] = {"name": name, "fqbn": fqbn}
    _save_user_boards()

    return DetectedDevice(
        port=unknown.port,
        name=name,
        fqbn=fqbn,
        vid=unknown.vid,
        pid=unknown.pid,
        serial_number=unknown.serial_number
    )