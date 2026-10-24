"""
Post-flash test definitions.

A sketch or PlatformIO project can describe its own tests in a flashbot.json
file next to the source (see flashbot.firmware.spec for the other keys):

    {
      "baud": 9600,
      "boot_delay": 2.0,
      "tests": [
        {"name": "boot_banner", "expect": "READY", "timeout": 5},
        {"name": "ping", "send": "PING", "expect": "PONG"},
        {"name": "status", "send": "STATUS", "expect": "^OK", "regex": true}
      ]
    }

Without a spec file the suite contains a single check that the serial port
opens after the board resets, which proves the new firmware booted far
enough to enumerate.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from flashbot.firmware.spec import SPEC_FILENAME, read_spec

DEFAULT_BAUD = 9600
DEFAULT_BOOT_DELAY = 2.0
_BAUD_RE = re.compile(r"\bSerial\w*\s*\.\s*begin\s*\(\s*(\d{3,7})")


@dataclass
class TestCase:
    __test__ = False  # not a pytest test class

    name: str
    send: str = ""
    expect: str = ""
    timeout: float = 2.0
    regex: bool = False

    def __post_init__(self):
        if self.regex and self.expect:
            re.compile(self.expect)  # surface bad patterns when the spec loads


@dataclass
class TestSuite:
    __test__ = False

    baud: int
    tests: list[TestCase] = field(default_factory=list)
    boot_delay: float = DEFAULT_BOOT_DELAY
    source: str = "default"


def detect_baud(directory: Path) -> Optional[int]:
    """Find the first Serial.begin(<baud>) call in the sketch or project sources."""
    candidates = sorted(directory.glob("*.ino")) + sorted(directory.glob("src/**/*.c*"))
    for path in candidates:
        try:
            match = _BAUD_RE.search(path.read_text(errors="ignore"))
        except OSError:
            continue
        if match:
            return int(match.group(1))
    return None


def load_suite(directory: Path, declared_baud: Optional[int] = None) -> TestSuite:
    """
    Build the test suite for a sketch directory. Baud rate precedence:
    flashbot.json, then the PlatformIO monitor_speed, then Serial.begin() in
    the source, then 9600.
    """
    spec_path = directory / SPEC_FILENAME
    spec = read_spec(directory)
    baud = spec.get("baud") or declared_baud or detect_baud(directory) or DEFAULT_BAUD

    tests = []
    for i, entry in enumerate(spec.get("tests", []), 1):
        if not isinstance(entry, dict):
            raise ValueError(f"{spec_path}: test #{i} must be an object")
        try:
            tests.append(TestCase(
                name=str(entry.get("name") or f"test_{i}"),
                send=str(entry.get("send", "")),
                expect=str(entry.get("expect", "")),
                timeout=float(entry.get("timeout", 2.0)),
                regex=bool(entry.get("regex", False)),
            ))
        except re.error as e:
            raise ValueError(f"{spec_path}: test #{i} has an invalid regex ({e})") from None

    return TestSuite(
        baud=int(baud),
        tests=tests or [TestCase("port_opens")],
        boot_delay=float(spec.get("boot_delay", DEFAULT_BOOT_DELAY)),
        source=SPEC_FILENAME if spec.get("tests") else "default",
    )
