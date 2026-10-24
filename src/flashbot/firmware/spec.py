"""
Reads flashbot.json, the optional per-sketch settings file.

    {
      "libraries": ["Adafruit BMP280 Library", "Servo@1.2.1"],
      "baud": 9600,
      "boot_delay": 2.0,
      "tests": [...]
    }

"libraries" lists Arduino libraries (optionally pinned with @version) that
are installed with arduino-cli before an Arduino sketch is compiled.
PlatformIO projects declare libraries with lib_deps in platformio.ini instead.
The test-related keys are described in flashbot.tester.test_cases.
"""

import json
from pathlib import Path

SPEC_FILENAME = "flashbot.json"


def read_spec(directory: Path) -> dict:
    """Parsed flashbot.json for a sketch directory, or {} if there is none."""
    path = Path(directory) / SPEC_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON ({e})") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    if not isinstance(data.get("tests", []), list):
        raise ValueError(f"{path}: 'tests' must be a list")
    libraries = data.get("libraries", [])
    if not isinstance(libraries, list) or not all(isinstance(x, str) and x.strip() for x in libraries):
        raise ValueError(f"{path}: 'libraries' must be a list of library names")
    return data


def required_libraries(directory: Path) -> list[str]:
    return [name.strip() for name in read_spec(directory).get("libraries", [])]
