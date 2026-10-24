"""Terminal presentation: panels, menus, and prompts shared by the CLI commands."""

from typing import Optional, Sequence

from rich import box
from rich.panel import Panel
from rich.markup import escape
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from flashbot import __version__
from flashbot.console import console, get_prefix, say
from flashbot.detector.boards import COMMON_BOARDS, BoardInfo, is_valid_fqbn
from flashbot.detector.device_id import DetectedDevice, UnknownBoard
from flashbot.firmware.scanner import is_new
from flashbot.firmware.targets import FirmwareTarget
from flashbot.pipeline.state_machine import PipelineResult, PipelineState
from flashbot.tester.test_runner import TestResult
from flashbot.workspace import Workspace

COMMON_BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

_STAGE_LABELS = {
    PipelineState.BUILDING: "Build",
    PipelineState.FLASHING: "Upload",
    PipelineState.TESTING: "Test",
}


# Panels ------------------------------------------------------------------

def banner(ws: Workspace) -> None:
    console.print(Panel.fit(
        f"[bold]FlashBot[/bold] [muted]{__version__}[/muted]\n"
        f"[muted]Workspace:[/muted] {ws.root}",
        border_style="cyan", padding=(0, 2),
    ))


def board_panel(device: DetectedDevice) -> None:
    if get_prefix():
        say(f"[bold green]{escape(device.name)}[/bold green] [muted]{device.fqbn}[/muted]")
        return
    body = Table.grid(padding=(0, 2))
    body.add_row("[muted]Port[/muted]", device.port)
    body.add_row("[muted]FQBN[/muted]", device.fqbn)
    body.add_row("[muted]USB ID[/muted]", f"{device.vid}:{device.pid}")
    if device.pio_board:
        body.add_row("[muted]PlatformIO[/muted]", device.pio_board)
    console.print(Panel(body, title=f"[bold green]{escape(device.name)}[/bold green]",
                        title_align="left", border_style="green"))


def unknown_panel(unknown: UnknownBoard) -> None:
    body = Table.grid(padding=(0, 2))
    body.add_row("[muted]Port[/muted]", unknown.port)
    body.add_row("[muted]USB ID[/muted]", f"{unknown.vid}:{unknown.pid}")
    body.add_row("[muted]Serial[/muted]", unknown.serial_number or "n/a")
    if unknown.description:
        body.add_row("[muted]Description[/muted]", unknown.description)
    console.print(Panel(body, title="[bold yellow]Unrecognised board[/bold yellow]",
                        title_align="left", border_style="yellow"))


def on_state_change(old: PipelineState, new: PipelineState) -> None:
    if new in _STAGE_LABELS:
        say(f"[info]>[/info] {_STAGE_LABELS[new]}")


def test_results(all_passed: bool, results: list[TestResult]) -> None:
    if get_prefix():
        for r in results:
            status = "[ok]PASS[/ok]" if r.passed else "[err]FAIL[/err]"
            say(f"  {status} {r.name}  [muted]{escape(r.detail)}[/muted]")
        return
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold", pad_edge=False)
    table.add_column("Test")
    table.add_column("Result", justify="center")
    table.add_column("Detail", overflow="fold")
    for r in results:
        status = Text("PASS", style="bold green") if r.passed else Text("FAIL", style="bold red")
        table.add_row(r.name, status, Text(r.detail, style="dim"))
    console.print(table)


def pipeline_summary(device: DetectedDevice, target: FirmwareTarget, result: PipelineResult) -> None:
    if result.success:
        tests = "tests skipped" if result.tests_passed is None else "all tests passed"
        say(f"[ok]Success[/ok]  {escape(target.label)} on {escape(device.name)}, {tests} "
            f"[muted]({result.duration:.1f}s)[/muted]")
    else:
        say(f"[err]Failed[/err]  {escape(target.label)} on {escape(device.name)}: {escape(result.error or '')} "
            f"[muted]({result.duration:.1f}s)[/muted]")


def no_targets_panel(device: DetectedDevice, ws: Workspace) -> None:
    if get_prefix():
        say(f"[warn]No firmware found for {device.fqbn}.[/warn]")
        return
    folder = "/".join(device.fqbn.replace(",", "/").split(":"))
    lines = [
        f"No firmware found for [bold]{device.fqbn}[/bold].",
        f"Add an Arduino sketch under [info]{ws.relpath(ws.sketches_dir)}/{folder}/<name>/<name>.ino[/info]",
    ]
    if device.pio_board:
        lines.append(f"or a PlatformIO project with [info]board = {device.pio_board}[/info].")
    console.print(Panel("\n".join(lines), title="No firmware", title_align="left", border_style="yellow"))


def targets_table(targets: Sequence[FirmwareTarget], title: Optional[str] = None) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold", title_justify="left")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", overflow="fold")
    table.add_column("Type")
    table.add_column("Board", overflow="fold")
    table.add_column("Path", style="dim", overflow="fold")
    for i, t in enumerate(targets, 1):
        name = Text(t.label)
        if is_new(t):
            name.append("  new", style="bold green")
        table.add_row(str(i), name, "PlatformIO" if t.kind == "platformio" else "Arduino",
                      t.board_label, t.path)
    return table


# Prompts -----------------------------------------------------------------

def choose(options: Sequence[str], prompt: str = "Select", default: Optional[int] = None) -> int:
    """Numbered menu; returns the zero-based index of the chosen option."""
    for i, option in enumerate(options, 1):
        console.print(f"  [info]{i:>2}[/info]  {option}")
    while True:
        choice = IntPrompt.ask(prompt, console=console, default=default)
        if choice is not None and 1 <= choice <= len(options):
            return choice - 1
        console.print(f"[err]Enter a number between 1 and {len(options)}.[/err]")


def select_target(device: DetectedDevice, targets: Sequence[FirmwareTarget]) -> Optional[FirmwareTarget]:
    """Returns the chosen target, None to skip this board, or raises SystemExit to quit."""
    console.print(f"\nFirmware available for [bold]{escape(device.name)}[/bold]:")
    options = []
    for t in targets:
        tag = "  [bold green]new[/bold green]" if is_new(t) else ""
        kind = "[muted]PlatformIO[/muted] " if t.kind == "platformio" else ""
        options.append(f"{kind}{escape(t.label)}{tag}  [muted]{escape(t.path)}[/muted]")
    options += ["[muted]Skip this board[/muted]", "[muted]Quit FlashBot[/muted]"]
    index = choose(options)
    if index == len(targets):
        return None
    if index == len(targets) + 1:
        raise SystemExit(0)
    return targets[index]


def select_board_type() -> Optional[tuple[str, str]]:
    """Returns (suggested name, fqbn) from the common board list, or a manual FQBN."""
    flat: list[tuple[str, str]] = []
    console.print("\n[bold]Select the board type[/bold]")
    for family, boards in COMMON_BOARDS.items():
        console.print(f"[muted]{family}[/muted]")
        for name, fqbn in boards:
            flat.append((name, fqbn))
            console.print(f"  [info]{len(flat):>2}[/info]  {name}")
    console.print(f"  [info]{len(flat) + 1:>2}[/info]  Other (enter an FQBN)")

    while True:
        choice = IntPrompt.ask("Select", console=console)
        if 1 <= choice <= len(flat):
            return flat[choice - 1]
        if choice == len(flat) + 1:
            break
        console.print(f"[err]Enter a number between 1 and {len(flat) + 1}.[/err]")

    console.print("[muted]Run 'arduino-cli board listall' to look up FQBNs.[/muted]")
    while True:
        fqbn = Prompt.ask("FQBN", console=console).strip()
        if is_valid_fqbn(fqbn):
            return "", fqbn
        console.print("[err]An FQBN looks like vendor:arch:board, for example arduino:avr:uno.[/err]")


def register_board(unknown: UnknownBoard) -> Optional[BoardInfo]:
    unknown_panel(unknown)
    if not Confirm.ask("Register this board?", default=True, console=console):
        return None
    suggested, fqbn = select_board_type()
    name = Prompt.ask("Board name", default=suggested or "My Board", console=console).strip()
    return BoardInfo(name=name or "My Board", fqbn=fqbn)


def baud_rate(default: int = 115200) -> int:
    console.print("\n[bold]Baud rate[/bold]")
    options = [f"{r}" + ("  [muted](detected)[/muted]" if r == default else "") for r in COMMON_BAUD_RATES]
    options.append("Custom")
    default_index = COMMON_BAUD_RATES.index(default) + 1 if default in COMMON_BAUD_RATES else len(options)
    index = choose(options, default=default_index)
    if index < len(COMMON_BAUD_RATES):
        return COMMON_BAUD_RATES[index]
    return IntPrompt.ask("Baud rate", default=default, console=console)


def post_flash_action() -> int:
    """0 = serial monitor, 1 = serial plotter, 2 = continue."""
    console.print("\n[bold]Next step[/bold]")
    return choose(["Open serial monitor", "Open serial plotter", "Continue"], default=3)
