"""
Workspace resolution.

A workspace is the directory FlashBot reads firmware from and writes its
configuration, build output, and logs to:

    <workspace>/
        sketches/   Arduino sketches and PlatformIO projects
        config/     user_boards.json, firmware_manifest.json
        build/      compiler output (one directory per board and sketch)
        logs/       flashbot.db

Resolution order:
    1. The --workspace command-line option
    2. The FLASHBOT_HOME environment variable
    3. The current directory, if it contains a sketches/ directory
    4. ~/.flashbot
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENV_VAR = "FLASHBOT_HOME"
DEFAULT_HOME = Path.home() / ".flashbot"


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def sketches_dir(self) -> Path:
        return self.root / "sketches"

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def build_dir(self) -> Path:
        return self.root / "build"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def db_path(self) -> Path:
        return self.logs_dir / "flashbot.db"

    @property
    def user_boards_path(self) -> Path:
        return self.config_dir / "user_boards.json"

    @property
    def manifest_path(self) -> Path:
        return self.config_dir / "firmware_manifest.json"

    def ensure(self) -> "Workspace":
        for d in (self.sketches_dir, self.config_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def relpath(self, path: Path) -> str:
        """Workspace-relative POSIX path when inside the workspace, absolute otherwise."""
        path = Path(path).resolve()
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def abspath(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.root / p


def resolve(explicit: Optional[str] = None) -> Workspace:
    if explicit:
        root = Path(explicit)
    elif os.environ.get(ENV_VAR):
        root = Path(os.environ[ENV_VAR])
    elif (Path.cwd() / "sketches").is_dir():
        root = Path.cwd()
    else:
        root = DEFAULT_HOME
    return Workspace(root.expanduser().resolve())


_current: Optional[Workspace] = None


def set_workspace(ws: Workspace) -> None:
    global _current
    _current = ws


def get_workspace() -> Workspace:
    global _current
    if _current is None:
        _current = resolve()
    return _current
