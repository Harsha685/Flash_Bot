"""Builds and uploads PlatformIO project environments with the pio CLI."""

import shutil
from pathlib import Path
from typing import Optional

from flashbot.console import say
from flashbot.firmware.targets import FirmwareTarget
from flashbot.flasher.base import BaseFlasher, StepResult, ToolNotFoundError, build_lock, run_tool, source_hash
from flashbot.workspace import Workspace


def find_pio() -> Optional[str]:
    for name in ("pio", "platformio"):
        found = shutil.which(name)
        if found:
            return found
    bundled = Path.home() / ".platformio" / "penv" / "bin" / "pio"
    return str(bundled) if bundled.exists() else None


class PlatformIOFlasher(BaseFlasher):
    """PlatformIO performs its own incremental builds, so no hash guard is needed."""

    def __init__(self, target: FirmwareTarget, workspace: Optional[Workspace] = None,
                 use_cache: bool = True):
        super().__init__(target, workspace)
        if not target.env:
            raise ValueError(f"PlatformIO target '{target.name}' has no environment")
        pio = find_pio()
        if not pio:
            raise ToolNotFoundError(
                "PlatformIO CLI not found. Install it with 'pipx install platformio' "
                "or see https://docs.platformio.org/en/latest/core/installation/"
            )
        self.pio = pio

    def _base(self) -> list[str]:
        return [self.pio, "run", "--project-dir", str(self.source_dir), "--environment", self.target.env]

    @property
    def _lock(self):
        return build_lock(f"{self.source_dir}::{self.target.env}")

    def build(self) -> StepResult:
        with self._lock:
            return self._build()

    def flash(self, port: str) -> StepResult:
        with self._lock:
            return self._flash(port)

    def _build(self) -> StepResult:
        digest = source_hash(self.source_dir, salt=self.target.env)
        proc = run_tool(self._base(), f"Building {self.target.label} with PlatformIO")
        if proc.returncode != 0:
            return StepResult(ok=False, error=self._failure("Build", proc))
        say("[ok]Build succeeded[/ok]")
        return StepResult(ok=True, source_hash=digest)

    def _flash(self, port: str) -> StepResult:
        proc = run_tool(self._base() + ["--target", "upload", "--upload-port", port],
                        f"Uploading {self.target.label} to {port}")
        if proc.returncode != 0:
            return StepResult(ok=False, error=self._failure("Upload", proc))
        say("[ok]Upload succeeded[/ok]")
        return StepResult(ok=True)
