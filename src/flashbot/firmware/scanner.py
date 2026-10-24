"""
Discovers firmware under <workspace>/sketches and writes firmware_manifest.json.

Two layouts are recognised anywhere in the tree:

    Arduino sketch      <vendor>/<arch>/<board>[/<option=value>...]/<name>/<name>.ino
                        The directory path encodes the FQBN, for example
                        arduino/avr/nano/cpu=atmega328old/blink/blink.ino
                        -> arduino:avr:nano:cpu=atmega328old

    PlatformIO project  any directory containing platformio.ini; each [env:...]
                        section becomes a separate target.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from flashbot.detector.boards import FQBN_TO_PIO
from flashbot.firmware.platformio import parse_platformio_ini
from flashbot.firmware.targets import ARDUINO, PLATFORMIO, FirmwareTarget
from flashbot.workspace import Workspace, get_workspace

NEW_THRESHOLD_HOURS = 24
SKIP_DIRS = {".pio", ".git", "build", ".vscode", "__pycache__"}
SOURCE_SUFFIXES = {".ino", ".pde", ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".s", ".S"}


@dataclass
class ScanResult:
    targets: list[FirmwareTarget] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def fqbn_from_parts(parts: list[str]) -> Optional[str]:
    """['arduino', 'avr', 'nano', 'cpu=atmega328old'] -> 'arduino:avr:nano:cpu=atmega328old'."""
    if len(parts) < 3:
        return None
    base, options = parts[:3], parts[3:]
    if any("=" not in opt for opt in options):
        return None
    return ":".join(base) + (":" + ",".join(options) if options else "")


def latest_mtime(directory: Path) -> float:
    newest = 0.0
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if Path(name).suffix in SOURCE_SUFFIXES or name == "platformio.ini":
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
    return newest


def _platformio_targets(project: Path, ws: Workspace, result: ScanResult) -> None:
    try:
        envs = parse_platformio_ini(project / "platformio.ini")
    except Exception as e:  # configparser raises several unrelated types
        result.warnings.append(f"{ws.relpath(project)}: could not parse platformio.ini ({e})")
        return
    if not envs:
        result.warnings.append(f"{ws.relpath(project)}: platformio.ini has no [env:...] sections")
        return
    mtime = latest_mtime(project)
    for env in envs:
        result.targets.append(FirmwareTarget(
            kind=PLATFORMIO, name=project.name, path=ws.relpath(project),
            fqbn=env.fqbn, env=env.name, pio_board=env.board,
            baud=env.monitor_speed, mtime=mtime,
        ))


def discover(ws: Optional[Workspace] = None) -> ScanResult:
    ws = ws or get_workspace()
    result = ScanResult()
    root = ws.sketches_dir
    if not root.is_dir():
        return result

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        here = Path(dirpath)

        if "platformio.ini" in filenames:
            _platformio_targets(here, ws, result)
            dirnames[:] = []
        elif f"{here.name}.ino" in filenames:
            parts = list(here.relative_to(root).parts[:-1])
            fqbn = fqbn_from_parts(parts)
            if fqbn:
                result.targets.append(FirmwareTarget(
                    kind=ARDUINO, name=here.name, path=ws.relpath(here),
                    fqbn=fqbn, pio_board=FQBN_TO_PIO.get(fqbn), mtime=latest_mtime(here),
                ))
            else:
                result.warnings.append(
                    f"{ws.relpath(here)}: cannot derive an FQBN from the path; expected "
                    "sketches/<vendor>/<arch>/<board>/<name>/<name>.ino"
                )
            dirnames[:] = []
        else:
            stray = [f for f in filenames if f.endswith(".ino")]
            for f in stray:
                result.warnings.append(
                    f"{ws.relpath(here / f)}: sketch file name must match its folder name"
                )

    result.targets.sort(key=lambda t: (-t.mtime, t.path, t.env or ""))
    return result


def targets_in(directory: Path, ws: Optional[Workspace] = None) -> ScanResult:
    """Targets defined by one sketch or project directory, which may be outside the workspace.
    Arduino sketches outside sketches/ have no FQBN; the caller must supply one."""
    ws = ws or get_workspace()
    directory = Path(directory).resolve()
    result = ScanResult()
    if (directory / "platformio.ini").is_file():
        _platformio_targets(directory, ws, result)
    elif (directory / f"{directory.name}.ino").is_file():
        try:
            fqbn = fqbn_from_parts(list(directory.relative_to(ws.sketches_dir.resolve()).parts[:-1]))
        except ValueError:
            fqbn = None
        result.targets.append(FirmwareTarget(
            kind=ARDUINO, name=directory.name, path=ws.relpath(directory), fqbn=fqbn,
            pio_board=FQBN_TO_PIO.get(fqbn or ""), mtime=latest_mtime(directory),
        ))
    return result


def write_manifest(result: ScanResult, ws: Optional[Workspace] = None) -> Path:
    ws = ws or get_workspace()
    ws.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 2,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "targets": [t.to_dict() for t in result.targets],
    }
    ws.manifest_path.write_text(json.dumps(data, indent=2) + "\n")
    return ws.manifest_path


def update_manifest(ws: Optional[Workspace] = None) -> ScanResult:
    result = discover(ws)
    write_manifest(result, ws)
    return result


def targets_for_device(device, targets: list[FirmwareTarget]) -> list[FirmwareTarget]:
    return [t for t in targets if t.matches(device)]


def is_new(target: FirmwareTarget) -> bool:
    return (time.time() - target.mtime) < NEW_THRESHOLD_HOURS * 3600
