"""A firmware target is one buildable unit: an Arduino sketch for a single FQBN,
or one environment of a PlatformIO project."""

from dataclasses import asdict, dataclass
from typing import Optional

ARDUINO = "arduino"
PLATFORMIO = "platformio"


@dataclass(frozen=True)
class FirmwareTarget:
    kind: str                         # ARDUINO or PLATFORMIO
    name: str                         # sketch or project directory name
    path: str                         # workspace-relative directory (absolute if outside)
    fqbn: Optional[str] = None        # Arduino FQBN, or explicit mapping for a PlatformIO env
    env: Optional[str] = None         # PlatformIO environment name
    pio_board: Optional[str] = None   # PlatformIO board ID
    baud: Optional[int] = None        # PlatformIO monitor_speed, if declared
    mtime: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.name} [{self.env}]" if self.kind == PLATFORMIO else self.name

    @property
    def board_label(self) -> str:
        if self.kind == PLATFORMIO:
            return self.fqbn or self.pio_board or "-"
        return self.fqbn or "-"

    def matches(self, device) -> bool:
        if self.kind == ARDUINO:
            return self.fqbn == device.fqbn
        if self.fqbn:
            return self.fqbn == device.fqbn
        return bool(self.pio_board) and self.pio_board == device.pio_board

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, "")}

    @classmethod
    def from_dict(cls, data: dict) -> "FirmwareTarget":
        fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in fields})
