"""Flasher factory. The pipeline asks for a flasher by target and never names a toolchain."""

from typing import Optional

from flashbot.firmware.targets import PLATFORMIO, FirmwareTarget
from flashbot.flasher.arduino_cli import ArduinoCliFlasher
from flashbot.flasher.base import BaseFlasher, StepResult, ToolNotFoundError
from flashbot.flasher.esp32 import Esp32Flasher
from flashbot.flasher.platformio import PlatformIOFlasher
from flashbot.workspace import Workspace

__all__ = ["get_flasher", "BaseFlasher", "StepResult", "ToolNotFoundError"]


def get_flasher(target: FirmwareTarget, workspace: Optional[Workspace] = None,
                use_cache: bool = True) -> BaseFlasher:
    if target.kind == PLATFORMIO:
        return PlatformIOFlasher(target, workspace, use_cache)
    arch = (target.fqbn or "").split(":")[1:2]
    if arch == ["esp32"]:
        return Esp32Flasher(target, workspace, use_cache)
    return ArduinoCliFlasher(target, workspace, use_cache)
