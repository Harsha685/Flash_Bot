import hashlib
import os
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flashbot.console import say, status as progress
from flashbot.firmware.scanner import SKIP_DIRS, SOURCE_SUFFIXES
from flashbot.firmware.targets import FirmwareTarget
from flashbot.workspace import Workspace, get_workspace


class ToolNotFoundError(RuntimeError):
    """The external build tool (arduino-cli, pio) is not installed."""


@dataclass
class StepResult:
    ok: bool
    error: Optional[str] = None
    skipped: bool = False
    source_hash: Optional[str] = None


def run_tool(cmd: list[str], status: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    try:
        with progress(status):
            return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError:
        raise ToolNotFoundError(f"'{cmd[0]}' was not found on PATH") from None


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def build_lock(key: str) -> threading.Lock:
    """One lock per build directory, so boards flashed in parallel never compile
    into, or upload from, the same directory at the same time."""
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def tail(text: str, lines: int = 25) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def source_hash(directory: Path, salt: str = "") -> str:
    """SHA-256 over every source file in the directory tree (names and contents)."""
    digest = hashlib.sha256(salt.encode())
    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if Path(name).suffix in SOURCE_SUFFIXES or name == "platformio.ini":
                files.append(Path(dirpath) / name)
    for path in sorted(files):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def summarize_error(output: str, limit: int = 200) -> str:
    """The most informative single line of tool output, for logs and CI reports."""
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if "error" in lowered or "failed" in lowered or "not found" in lowered:
            return line[:limit]
    return lines[-1][:limit] if lines else ""


def diagnose(output: str) -> Optional[str]:
    """Translate common toolchain failures into an actionable hint."""
    text = output.lower()
    if "permission denied" in text and "/dev/" in text:
        return "Add your user to the 'dialout' group (sudo usermod -aG dialout $USER), then log out and back in."
    if "resource busy" in text or "could not open port" in text:
        return "Another process holds the port. Close other serial monitors and stop ModemManager."
    if "no such file or directory" in text and "/dev/" in text:
        return "The board disconnected or changed port during upload. Reconnect it and try again."
    return None


class BaseFlasher(ABC):
    def __init__(self, target: FirmwareTarget, workspace: Optional[Workspace] = None):
        self.target = target
        self.ws = workspace or get_workspace()
        self.source_dir = self.ws.abspath(target.path)

    @abstractmethod
    def build(self) -> StepResult:
        """Compile the target."""

    @abstractmethod
    def flash(self, port: str) -> StepResult:
        """Upload the compiled firmware to the board on `port`."""

    def _failure(self, step: str, proc: subprocess.CompletedProcess) -> str:
        output = (proc.stderr or "") + (proc.stdout or "")
        say(f"[err]{step} failed[/err]")
        for line in tail(output).splitlines():
            say(line, markup=False, style="dim")
        hint = diagnose(output)
        if hint:
            say(f"[warn]Hint:[/warn] {hint}")
        reason = summarize_error(output)
        return f"{step} failed: {reason}" if reason else f"{step} failed"
