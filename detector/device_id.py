from dataclasses import dataclass
from typing import Optional

# Board lookup table — keyed by (vid, pid) as lowercase hex strings without 0x prefix
BOARD_TABLE = {
    ("2341", "0043"): {"name": "Arduino Uno",         "fqbn": "arduino:avr:uno"},
    ("2341", "1002"): {"name": "Arduino Uno WiFi R4",  "fqbn": "arduino:renesas_uno:unor4wifi"},
    ("2341", "0010"): {"name": "Arduino Mega",         "fqbn": "arduino:avr:mega"},
    ("2341", "8036"): {"name": "Arduino Leonardo",     "fqbn": "arduino:avr:leonardo"},
    ("2341", "8037"): {"name": "Arduino Micro",        "fqbn": "arduino:avr:micro"},
}

@dataclass
class DetectedDevice:
    port: str
    name: str
    fqbn: str
    vid: str
    pid: str
    serial_number: str

def detect_from_udev(udev_device) -> Optional[DetectedDevice]:
    # read all identifiers directly from the udev event object
    vid    = udev_device.get("ID_VENDOR_ID",   "").lower()
    pid    = udev_device.get("ID_MODEL_ID",    "").lower()
    port   = udev_device.get("DEVNAME",        "")
    serial = udev_device.get("ID_SERIAL_SHORT","")
    board = BOARD_TABLE.get((vid, pid))
    if not board:
        return None

    return DetectedDevice(
        port=port,
        name=board["name"],
        fqbn=board["fqbn"],
        vid=vid,
        pid=pid,
        serial_number=serial
    )