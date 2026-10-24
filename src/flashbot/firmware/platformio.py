"""Minimal platformio.ini reader: environments, boards, and monitor speeds."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Optional per-environment key that pins an environment to an exact FQBN,
# for boards whose PlatformIO ID FlashBot cannot infer.
FQBN_OPTION = "custom_flashbot_fqbn"


@dataclass
class PioEnv:
    name: str
    board: Optional[str]
    platform: Optional[str]
    framework: Optional[str]
    monitor_speed: Optional[int]
    fqbn: Optional[str]


def _read(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(
        interpolation=None, strict=False, inline_comment_prefixes=(";", "#"),
    )
    parser.read(path, encoding="utf-8")
    return parser


def _resolve(parser: configparser.ConfigParser, section: str, seen: set) -> dict:
    """Merge [env], any 'extends' chain, and the section itself (later wins)."""
    if section in seen or not parser.has_section(section):
        return {}
    seen.add(section)
    values = dict(parser["env"]) if parser.has_section("env") and section != "env" else {}
    for parent in (s.strip() for s in parser[section].get("extends", "").split(",")):
        if parent:
            values.update(_resolve(parser, parent, seen))
    values.update(parser[section])
    return values


def _int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def parse_platformio_ini(path: Path) -> list[PioEnv]:
    parser = _read(Path(path))
    envs = []
    for section in parser.sections():
        if not section.startswith("env:"):
            continue
        values = _resolve(parser, section, set())
        envs.append(PioEnv(
            name=section[len("env:"):],
            board=values.get("board") or None,
            platform=values.get("platform") or None,
            framework=values.get("framework") or None,
            monitor_speed=_int(values.get("monitor_speed")),
            fqbn=values.get(FQBN_OPTION) or None,
        ))
    return envs
