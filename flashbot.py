#!/usr/bin/env python3
"""
FlashBot Rich CLI
=================
A single-file Rich UI that connects all existing modules.
Run with: python flashbot.py
"""

import json
import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import IntPrompt, Confirm, Prompt
from rich.status import Status
from rich import box

from detector.usb_listener import start_listener
from detector.device_id import detect_from_udev, UnknownBoard
from detector.device_id import BOARD_TABLE, _save_user_boards
from flasher import get_flasher
from logger.result_store import init_db, save_result
from tester.test_cases import get_tests_for_sketch
from tester.test_runner import TestRunner
from config.sketch_scanner import update_manifest
import pyudev

# ── Global State ──────────────────────────────────────────────
console = Console()
_flashing = False
_shutdown = False
_flash_cooldown = {}


# ── UI Helpers ───────────────────────────────────────────────
def show_banner():
    console.print(Panel.fit(
        "[bold cyan]FlashBot[/bold cyan]  [dim]v0.1.0-alpha[/dim]\n"
        "[dim]Plug in a board. FlashBot handles the rest.[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))


def show_board_detected(device):
    console.print(Panel(
        f"[bold]{device.name}[/bold]\n"
        f"[dim]Port:[/dim]  {device.port}\n"
        f"[dim]FQBN:[/dim]  {device.fqbn}",
        title="[green]Board Detected[/green]",
        border_style="green",
    ))


def show_unknown_board(unknown):
    console.print(Panel(
        f"[bold]Port:[/bold]   {unknown.port}\n"
        f"[bold]VID:[/bold]    {unknown.vid}\n"
        f"[bold]PID:[/bold]    {unknown.pid}\n"
        f"[bold]Serial:[/bold] {unknown.serial_number or 'N/A'}",
        title="[yellow]Unknown Board[/yellow]",
        border_style="yellow",
    ))


def show_registered(name, fqbn):
    console.print(Panel(
        f"[bold green]Registered[/bold green] {name}\n"
        f"[dim]FQBN:[/dim] {fqbn}",
        title="New Board",
        border_style="green",
    ))


def show_flash_result(ok: bool):
    color = "bold green" if ok else "bold red"
    text = "FLASH OK" if ok else "FLASH FAIL"
    console.print(f"[{color}]{text}[/{color}]")


def show_test_result(all_passed: bool, results: list):
    color = "bold green" if all_passed else "bold red"
    text = "All Tests Passed" if all_passed else "Some Tests Failed"
    console.print(f"[{color}]{text}[/{color}]")
    for r in results:
        icon = "✓" if r["passed"] else "✗"
        status_color = "green" if r["passed"] else "red"
        console.print(f"  [{status_color}]{icon} {r['name']}[/{status_color}]")


# ── Prompts ──────────────────────────────────────────────────
def prompt_register_board(unknown: UnknownBoard):
    show_unknown_board(unknown)
    if not Confirm.ask("Register this board?", default=True, console=console):
        return None

    name = Prompt.ask("Enter board name", default="My Board", console=console)
    fqbn = Prompt.ask("Enter FQBN", default="arduino:avr:uno", console=console)

    if not name or not fqbn:
        console.print("[red]Name and FQBN required. Skipping.[/red]")
        return None

    BOARD_TABLE[(unknown.vid, unknown.pid)] = {"name": name, "fqbn": fqbn}
    _save_user_boards()
    show_registered(name, fqbn)

    from detector.device_id import DetectedDevice
    return DetectedDevice(
        port=unknown.port,
        name=name,
        fqbn=fqbn,
        vid=unknown.vid,
        pid=unknown.pid,
        serial_number=unknown.serial_number,
    )


def prompt_sketch_selection(device, sketches: list) -> Optional[str]:
    if len(sketches) == 1:
        console.print(f"[dim]Auto-selected:[/dim] {sketches[0]}")
        return sketches[0]

    console.print(f"\n[bold cyan]{device.name}[/bold cyan] — Available sketches:")
    for i, sketch in enumerate(sketches, 1):
        console.print(f"  {i}. {sketch}")
    console.print(f"  {len(sketches) + 1}. [dim]Exit[/dim]")

    while True:
        choice = IntPrompt.ask("Select", console=console)
        if choice == len(sketches) + 1:
            return None
        if 1 <= choice <= len(sketches):
            return sketches[choice - 1]
        console.print("[red]Invalid choice.[/red]")


# ── Core Pipeline ──────────────────────────────────────────────
def run_pipeline(device):
    global _flash_cooldown

    with open("config/firmware_manifest.json", "r") as f:
        manifest = json.load(f)

    sketches = manifest.get(device.fqbn, {}).get("sketches", [])
    if not sketches:
        console.print(Panel(
            f"[yellow]No sketches configured for {device.fqbn}[/yellow]\n"
            f"[dim]Drop a .ino into sketches/{device.fqbn.replace(':', '/')}/[/dim]",
            title="Missing Sketches",
            border_style="yellow",
        ))
        return

    while True:
        sketch_path = prompt_sketch_selection(device, sketches)
        if sketch_path is None:
            console.print("[dim]Returning to listener...[/dim]")
            break

        flasher = get_flasher(device.fqbn)
        try:
            with Status("[bold yellow]Building & Flashing...", spinner="dots", console=console):
                ok, source_hash = flasher.run(device.port, sketch_path, device.name)
            show_flash_result(ok)
            flash_status = "success" if ok else "failed"
            flash_error = None if ok else "Build or flash step failed"
        except Exception as e:
            flash_status = "failed"
            flash_error = str(e)
            source_hash = None
            console.print(f"[bold red]FLASH ERROR: {e}[/]")

        save_result(device.name, device.fqbn, device.port, sketch_path,
                    flash_status, flash_error, source_hash)
        console.print("[dim]Logged to database[/dim]")

        if flash_status == "success":
            _flash_cooldown[device.serial_number or device.port] = time.time()

            tests = get_tests_for_sketch(sketch_path)
            if tests:
                try:
                    with Status("[bold blue]Running serial tests...", spinner="bouncingBall", console=console):
                        runner = TestRunner(device.port)
                        all_passed, results = runner.run_all(tests)
                    show_test_result(all_passed, results)
                except Exception as e:
                    console.print(f"[red]TEST ERROR: {e}[/red]")

        if not Confirm.ask("Flash another sketch?", default=False, console=console):
            console.print("[dim]Returning to listener...[/dim]")
            break


# ── Event Handlers ────────────────────────────────────────────
def on_device(device):
    global _flashing
    if _flashing:
        return
    _flashing = True
    try:
        show_board_detected(device)
        run_pipeline(device)
    finally:
        _flashing = False


def on_unknown(unknown):
    global _flashing
    if _flashing:
        return
    _flashing = True
    try:
        device = prompt_register_board(unknown)
        if device:
            run_pipeline(device)
    finally:
        _flashing = False


def check_already_connected():
    context = pyudev.Context()
    for dev in context.list_devices(subsystem="tty"):
        if dev.get("ID_VENDOR_ID"):
            result = detect_from_udev(dev)
            if isinstance(result, UnknownBoard):
                on_unknown(result)
            elif result:
                on_device(result)


# ── Reporter ─────────────────────────────────────────────────
def reporter_cli():
    from logger.result_store import get_results
    import datetime

    init_db()
    rows = get_results()

    if not rows:
        console.print(Panel("[yellow]No flash runs found.[/yellow]", title="History"))
        return

    table = Table(
        title="Flash History",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("ID", style="dim", width=5)
    table.add_column("Board", min_width=18)
    table.add_column("FQBN", min_width=25)
    table.add_column("Sketch", min_width=22)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Timestamp", min_width=19)

    for row in rows:
        status_str = "SUCCESS" if row[5] == "success" else "FAILED"
        status_style = "bold green" if row[5] == "success" else "bold red"
        table.add_row(
            str(row[0]), row[1], row[2], row[4],
            f"[{status_style}]{status_str}[/{status_style}]",
            row[7],
        )

    console.print(table)

    since = datetime.datetime.now() - datetime.timedelta(days=7)
    failed = [
        r for r in rows
        if r[5] == "failed"
        and datetime.datetime.strptime(r[7], "%Y-%m-%d %H:%M:%S") > since
    ]

    if failed:
        console.print()
        ftable = Table(
            title="Failed Runs (last 7 days)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold red",
        )
        ftable.add_column("ID", style="dim", width=5)
        ftable.add_column("Board", min_width=18)
        ftable.add_column("Sketch", min_width=22)
        ftable.add_column("Error", min_width=25)
        ftable.add_column("Timestamp", min_width=19)
        for row in failed:
            ftable.add_row(
                str(row[0]), row[1], row[4],
                str(row[6] or "—"),
                row[7],
            )
        console.print(ftable)
    else:
        console.print(Panel(
            "[green]No failed runs in the last 7 days.[/green]",
            title="Failures",
        ))


# ── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        reporter_cli()
        sys.exit(0)

    show_banner()
    init_db()
    update_manifest()
    check_already_connected()
    start_listener(on_device, on_unknown=on_unknown)

    console.print("[dim]Listening for USB devices... (Ctrl+C to quit)[/dim]")
    try:
        while not _shutdown:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    console.print("[bold red]Stopping.[/bold red]")
