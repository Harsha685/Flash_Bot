"""
Shared Rich console so every module writes to the same terminal stream.

When several boards are flashed in parallel, each worker thread sets a prefix
(the board's port) so interleaved lines stay attributable. Spinners are only
shown on the main thread, because Rich allows a single live display at a time.
"""

import threading
from contextlib import contextmanager, nullcontext
from typing import Iterator

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

console = Console(theme=Theme({
    "info": "cyan",
    "ok": "bold green",
    "warn": "yellow",
    "err": "bold red",
    "muted": "dim",
}))

_local = threading.local()


def get_prefix() -> str:
    return getattr(_local, "prefix", "")


@contextmanager
def output_prefix(prefix: str) -> Iterator[None]:
    previous = get_prefix()
    _local.prefix = prefix
    try:
        yield
    finally:
        _local.prefix = previous


def say(message: str = "", *, markup: bool = True, style: str = "") -> None:
    """Print a line, prefixed with the current thread's board label if one is set."""
    text = Text.from_markup(message, style=style) if markup else Text(message, style=style)
    prefix = get_prefix()
    if prefix:
        text = Text.assemble((f"[{prefix}] ", "bold cyan"), text)
    console.print(text, highlight=False)


def status(message: str):
    """A spinner on the main thread; a plain progress line in worker threads."""
    if get_prefix() or threading.current_thread() is not threading.main_thread():
        say(f"[muted]{message}...[/muted]")
        return nullcontext()
    return console.status(message)
