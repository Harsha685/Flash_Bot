"""Environment checks for `flashbot doctor`."""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

from rich import box
from rich.table import Table
from rich.text import Text

from flashbot.console import console
from flashbot.firmware.scanner import discover
from flashbot.flasher.platformio import find_pio
from flashbot.workspace import Workspace

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_STYLE = {PASS: "bold green", WARN: "bold yellow", FAIL: "bold red"}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _python() -> Check:
    ok = sys.version_info >= (3, 10)
    return Check("Python", PASS if ok else FAIL, sys.version.split()[0])


def _arduino_cli() -> list[Check]:
    if not shutil.which("arduino-cli"):
        return [Check("arduino-cli", FAIL, "not found on PATH; required for Arduino sketches")]
    version = _run(["arduino-cli", "version"]).replace("arduino-cli", "").strip()
    checks = [Check("arduino-cli", PASS, version.split(" Commit")[0] or "installed")]
    cores = [line.split()[0] for line in _run(["arduino-cli", "core", "list"]).splitlines()[1:] if line.strip()]
    checks.append(Check("Arduino cores", PASS if cores else WARN,
                        ", ".join(cores) if cores else "none installed; see 'arduino-cli core install'"))
    return checks


def _platformio() -> Check:
    pio = find_pio()
    if not pio:
        return Check("PlatformIO", WARN, "not installed; only needed for PlatformIO projects")
    return Check("PlatformIO", PASS, _run([pio, "--version"]).replace("PlatformIO Core, version", "").strip())


def _serial_permissions() -> Check:
    if not sys.platform.startswith("linux"):
        return Check("Serial permissions", PASS, "not applicable on this platform")
    import grp
    groups = {grp.getgrgid(g).gr_name for g in os.getgroups()}
    wanted = {"dialout", "uucp"} & {g.gr_name for g in grp.getgrall()}
    if not wanted or groups & wanted:
        return Check("Serial permissions", PASS, "user can access serial ports")
    return Check("Serial permissions", FAIL,
                 f"add your user to '{sorted(wanted)[0]}': sudo usermod -aG {sorted(wanted)[0]} $USER")


def _hotplug() -> Check:
    try:
        import pyudev  # noqa: F401
        return Check("Hotplug detection", PASS, "udev")
    except ImportError:
        return Check("Hotplug detection", WARN, "pyudev unavailable; falling back to polling")


def _modem_manager() -> Check:
    if not shutil.which("systemctl"):
        return Check("ModemManager", PASS, "not present")
    state = _run(["systemctl", "is-active", "ModemManager"])
    if state == "active":
        return Check("ModemManager", WARN, "running; it can grab new serial ports. "
                                           "Consider 'sudo systemctl disable --now ModemManager'")
    return Check("ModemManager", PASS, "not running")


def _workspace(ws: Workspace) -> Check:
    if not ws.sketches_dir.is_dir():
        return Check("Workspace", WARN, f"{ws.root} has no sketches/ directory; run 'flashbot init'")
    result = discover(ws)
    detail = f"{ws.root} ({len(result.targets)} firmware targets"
    detail += f", {len(result.warnings)} warnings)" if result.warnings else ")"
    return Check("Workspace", WARN if result.warnings else PASS, detail)


def run_doctor(ws: Workspace) -> int:
    checks = [_python(), *_arduino_cli(), _platformio(), _serial_permissions(),
              _hotplug(), _modem_manager(), _workspace(ws)]
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Check")
    table.add_column("Status", justify="center")
    table.add_column("Detail", overflow="fold")
    for c in checks:
        table.add_row(c.name, Text(c.status, style=_STYLE[c.status]), c.detail)
    console.print(table)
    return 1 if any(c.status == FAIL for c in checks) else 0
