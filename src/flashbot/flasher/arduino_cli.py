"""
Builds and uploads Arduino sketches with arduino-cli.

Works for any installed core (AVR, megaAVR, SAMD, Renesas, RP2040, Teensy,
STM32, ...). Each sketch/FQBN pair gets its own build directory so the
hash guard can never upload a binary that belongs to a different sketch.
"""

import re
import time
from typing import Optional

from flashbot.console import say
from flashbot.detector.boards import fqbn_platform
from flashbot.firmware.spec import required_libraries
from flashbot.firmware.targets import FirmwareTarget
from flashbot.flasher.base import BaseFlasher, StepResult, build_lock, run_tool, source_hash
from flashbot.logger.result_store import get_last_build_hash
from flashbot.workspace import Workspace

ARTIFACT_SUFFIXES = (".bin", ".hex", ".uf2", ".elf")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


class ArduinoCliFlasher(BaseFlasher):
    cli = "arduino-cli"
    upload_attempts = 1
    upload_hint: Optional[str] = None

    def __init__(self, target: FirmwareTarget, workspace: Optional[Workspace] = None,
                 use_cache: bool = True):
        super().__init__(target, workspace)
        if not target.fqbn:
            raise ValueError(f"Sketch '{target.name}' has no FQBN")
        self.fqbn = target.fqbn
        self.use_cache = use_cache
        self.build_dir = self.ws.build_dir / _safe(self.fqbn) / _safe(target.name)

    def _has_artifacts(self) -> bool:
        return self.build_dir.is_dir() and any(
            p.suffix in ARTIFACT_SUFFIXES for p in self.build_dir.iterdir()
        )

    def build(self) -> StepResult:
        with build_lock(str(self.build_dir)):
            return self._build()

    def flash(self, port: str) -> StepResult:
        with build_lock(str(self.build_dir)):
            return self._flash(port)

    def _build(self) -> StepResult:
        digest = source_hash(self.source_dir, salt=self.fqbn)
        if (self.use_cache and self._has_artifacts()
                and get_last_build_hash(self.fqbn, self.target.path) == digest):
            say("[muted]Sources unchanged since the last successful build; skipping compile.[/muted]")
            return StepResult(ok=True, skipped=True, source_hash=digest)

        libraries = required_libraries(self.source_dir)
        if libraries:
            proc = run_tool([self.cli, "lib", "install", *libraries],
                            f"Installing libraries: {', '.join(libraries)}")
            if proc.returncode != 0:
                return StepResult(ok=False, error=self._failure("Library installation", proc))

        self.build_dir.mkdir(parents=True, exist_ok=True)
        proc = run_tool(
            [self.cli, "compile", "--fqbn", self.fqbn, "--build-path", str(self.build_dir),
             str(self.source_dir)],
            f"Compiling {self.target.name} for {self.fqbn}",
        )
        if proc.returncode != 0:
            error = self._failure("Build", proc)
            output = (proc.stderr + proc.stdout).lower()
            if "platform" in output and ("not installed" in output or "not found" in output):
                say(f"[warn]Hint:[/warn] install the core with "
                              f"'arduino-cli core install {fqbn_platform(self.fqbn)}'.")
            return StepResult(ok=False, error=error)

        say("[ok]Build succeeded[/ok]")
        return StepResult(ok=True, source_hash=digest)

    def _flash(self, port: str) -> StepResult:
        cmd = [self.cli, "upload", "--port", port, "--fqbn", self.fqbn,
               "--input-dir", str(self.build_dir), str(self.source_dir)]
        proc = None
        for attempt in range(1, self.upload_attempts + 1):
            label = f"Uploading to {port}" + (f" (attempt {attempt})" if attempt > 1 else "")
            proc = run_tool(cmd, label)
            if proc.returncode == 0:
                say("[ok]Upload succeeded[/ok]")
                return StepResult(ok=True)
            if attempt < self.upload_attempts:
                time.sleep(1)

        error = self._failure("Upload", proc)
        if self.upload_hint:
            say(f"[warn]Hint:[/warn] {self.upload_hint}")
        return StepResult(ok=False, error=error)
