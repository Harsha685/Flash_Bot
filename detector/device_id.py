from dataclasses import dataclass
from typing import Optional

BOARD_TABLE = {
    ("2341", "0043"): {"name": "Arduino Uno",            "fqbn": "arduino:avr:uno"},
    ("2341", "1002"): {"name": "Arduino Uno R4 WiFi",    "fqbn": "arduino:renesas_uno:unor4wifi"},
    ("2341", "0010"): {"name": "Arduino Mega",           "fqbn": "arduino:avr:mega"},
    ("2341", "8036"): {"name": "Arduino Leonardo",       "fqbn": "arduino:avr:leonardo"},
    ("2341", "8037"): {"name": "Arduino Micro",          "fqbn": "arduino:avr:micro"},
    ("2341", "6001"): {"name": "Arduino Nano",           "fqbn": "arduino:avr:nano"},
    ("1a86", "7523"): {"name": "Arduino Nano (CH340)",   "fqbn": "arduino:avr:nano"},
    ("0403", "6001"): {"name": "Arduino Nano (FTDI)",    "fqbn": "arduino:avr:nano"},
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
    vid    = udev_device.get("ID_VENDOR_ID",    "").lower()
    pid    = udev_device.get("ID_MODEL_ID",     "").lower()
    port   = udev_device.get("DEVNAME",         "")
    serial = udev_device.get("ID_SERIAL_SHORT", "")

    if not vid or not pid:
        return None

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

def detect_single(port: Optional[str] = None) -> Optional[DetectedDevice]:
    import subprocess, json
    try:
        result = subprocess.run(
            ["arduino-cli", "board", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
    except Exception:
        return None

    for entry in data.get("detected_ports", []):
        port_info = entry.get("port", {})
        props = port_info.get("properties", {})

        vid = props.get("vid", "").lower().replace("0x", "")
        pid = props.get("pid", "").lower().replace("0x", "")

        if port and port_info.get("address") != port:
            continue

        if not vid or not pid:
            continue

        board = BOARD_TABLE.get((vid, pid))
        if not board:
            continue

        return DetectedDevice(
            port=port_info.get("address", ""),
            name=board["name"],
            fqbn=board["fqbn"],
            vid=vid,
            pid=pid,
            serial_number=props.get("serialNumber", "")
        )

    return None

if __name__ == "__main__":
    print(detect_single())
