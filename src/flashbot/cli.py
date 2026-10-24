"""FlashBot command-line interface."""

import argparse
import dataclasses
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from rich import box
from rich.markup import escape
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from flashbot import __version__, ui
from flashbot.console import console, output_prefix, say
from flashbot.detector.boards import FQBN_TO_PIO, BoardInfo, BoardRegistry, is_valid_fqbn
from flashbot.detector.device_id import (
    DetectedDevice, PortInfo, UnknownBoard, connected_devices, find_port, identify, list_serial_ports,
)
from flashbot.detector.usb_listener import start_listener
from flashbot.firmware.scanner import ScanResult, discover, targets_for_device, targets_in, update_manifest
from flashbot.firmware.targets import ARDUINO, FirmwareTarget
from flashbot.flasher import ToolNotFoundError, get_flasher
from flashbot.logger import export
from flashbot.logger.reporter import print_report
from flashbot.pipeline.state_machine import PipelineResult, PipelineStateMachine
from flashbot.tools.serial_base import guess_port
from flashbot.tools.serial_monitor import SerialMonitor
from flashbot.tools.serial_plotter import SerialPlotter
from flashbot.workspace import Workspace, get_workspace, resolve, set_workspace

# Ignore hotplug events from a board this many seconds after its pipeline finishes;
# most boards reset and re-enumerate after an upload.
REENUMERATION_COOLDOWN = 8.0


class UsageError(Exception):
    """A problem with the command-line input; reported without a traceback."""


# Shared helpers -----------------------------------------------------------

def _warn_scan(result: ScanResult) -> None:
    for warning in result.warnings:
        console.print(f"[warn]Warning:[/warn] {escape(warning)}")


def _run_pipeline(device: DetectedDevice, target: FirmwareTarget, ws: Workspace,
                  run_tests: bool, use_cache: bool) -> PipelineResult:
    say(f"[bold]{escape(target.label)}[/bold] [muted]-> {escape(device.name)} ({device.port})[/muted]")
    machine = PipelineStateMachine(
        on_state_change=ui.on_state_change, on_test_result=ui.test_results,
        workspace=ws, run_tests=run_tests, use_cache=use_cache,
    )
    result = machine.run(device, target)
    ui.pipeline_summary(device, target, result)
    return result


def _resolve_targets(spec: Optional[str], ws: Workspace, scan: ScanResult) -> list[FirmwareTarget]:
    """A target can be a sketch/project path, a sketch name, or omitted (all targets)."""
    if not spec:
        return list(scan.targets)
    for candidate in (Path(spec), ws.root / spec):
        if candidate.exists():
            directory = candidate.parent if candidate.is_file() else candidate
            found = targets_in(directory, ws).targets
            if not found:
                raise UsageError(f"{spec} is not an Arduino sketch or PlatformIO project")
            return found
    found = [t for t in scan.targets if spec in (t.name, t.label)]
    if not found:
        raise UsageError(f"No sketch or project named '{spec}'. Run 'flashbot sketches' to list them.")
    return found


def _filter(targets: list[FirmwareTarget], fqbn: Optional[str], env: Optional[str]) -> list[FirmwareTarget]:
    out = []
    for t in targets:
        if env and t.env != env:
            continue
        if fqbn and t.kind == ARDUINO:
            if t.fqbn is None:
                t = dataclasses.replace(t, fqbn=fqbn)
            elif t.fqbn != fqbn:
                continue
        elif fqbn and not (t.fqbn == fqbn or (t.pio_board and t.pio_board == FQBN_TO_PIO.get(fqbn))):
            continue
        out.append(t)
    return out


# run ----------------------------------------------------------------------

class Session:
    """
    Dispatches hotplug events. Interactive sessions handle boards one at a time on
    the main thread, so prompts and Ctrl+C behave normally. Unattended sessions
    with jobs > 1 hand each board to a worker thread and flash several at once.
    """

    def __init__(self, ws: Workspace, auto: bool, sketch: Optional[str], run_tests: bool,
                 use_cache: bool, jobs: int = 1):
        self.ws = ws
        self.auto = auto
        self.sketch = sketch
        self.run_tests = run_tests
        self.use_cache = use_cache
        self.registry = BoardRegistry()
        self.cooldown_until: dict[str, float] = {}
        self.active: set[str] = set()
        self._lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=jobs, thread_name_prefix="flashbot-board") if jobs > 1 else None

    def handle(self, event_time: float, info: PortInfo) -> None:
        with self._lock:
            if info.key in self.active or event_time <= self.cooldown_until.get(info.key, float("-inf")):
                return
        found = identify(info, self.registry)
        if found is None:
            return
        if isinstance(found, UnknownBoard):
            if self.auto:
                say(f"[warn]Skipping unrecognised board {found.vid}:{found.pid} on {found.port}.[/warn] "
                    "[muted]Register it with 'flashbot boards add'.[/muted]")
                self._cool(info.key)
                return
            found = self._register(found)
            if found is None:
                self._cool(info.key)
                return

        with self._lock:
            self.active.add(info.key)
        if self.pool:
            self.pool.submit(self._worker, info.key, found)
        else:
            self._worker(info.key, found)

    def shutdown(self) -> None:
        if self.pool:
            self.pool.shutdown(wait=False, cancel_futures=True)

    def _cool(self, *keys: str) -> None:
        until = time.time() + REENUMERATION_COOLDOWN
        with self._lock:
            for key in keys:
                self.cooldown_until[key] = until

    def _worker(self, key: str, device: DetectedDevice) -> None:
        label = Path(device.port).name if self.pool else ""
        try:
            with output_prefix(label):
                self._serve(device)
        except Exception as e:  # keep the session alive if one board fails unexpectedly
            say(f"[err]Unexpected error on {device.port}:[/err] {escape(str(e))}")
        finally:
            with self._lock:
                self.active.discard(key)
            # The board may have re-enumerated on a new port; ignore both identities briefly.
            self._cool(key, device.key)

    def _register(self, unknown: UnknownBoard) -> Optional[DetectedDevice]:
        info = ui.register_board(unknown)
        if not info:
            return None
        self.registry.register(unknown.vid, unknown.pid, info)
        console.print(f"[ok]Registered[/ok] {escape(info.name)} ({info.fqbn}) "
                      f"[muted]in {self.ws.relpath(self.registry.path)}[/muted]")
        return DetectedDevice(port=unknown.port, name=info.name, fqbn=info.fqbn, vid=unknown.vid,
                              pid=unknown.pid, serial_number=unknown.serial_number, pio_board=info.pio_board)

    def _pick(self, device: DetectedDevice, targets: list[FirmwareTarget]) -> Optional[FirmwareTarget]:
        if self.sketch:
            named = [t for t in targets if self.sketch in (t.name, t.label)]
            if not named:
                say(f"[warn]No firmware named '{escape(self.sketch)}' for {device.fqbn}; skipping.[/warn]")
                return None
            targets = named
        if self.auto or len(targets) == 1:
            say(f"[muted]Selected {escape(targets[0].label)} ({escape(targets[0].path)})[/muted]")
            return targets[0]
        return ui.select_target(device, targets)

    def _serve(self, device: DetectedDevice) -> None:
        ui.board_panel(device)
        while True:
            targets = targets_for_device(device, discover(self.ws).targets)
            if not targets:
                ui.no_targets_panel(device, self.ws)
                return
            target = self._pick(device, targets)
            if target is None:
                return
            result = _run_pipeline(device, target, self.ws, self.run_tests, self.use_cache)
            device.port = result.port or device.port
            if self.auto:
                return
            if result.flashed:
                action = ui.post_flash_action()
                if action in (0, 1):
                    baud = ui.baud_rate(result.baud or 115200)
                    tool = SerialMonitor(device.port, baud) if action == 0 else SerialPlotter(device.port, baud)
                    tool.run()
            if not Confirm.ask("Flash another sketch to this board?", default=False, console=console):
                return


def cmd_run(args, ws: Workspace) -> int:
    if args.jobs < 1:
        raise UsageError("--jobs must be at least 1")
    if args.jobs > 1 and not args.auto:
        raise UsageError("--jobs requires --auto; interactive sessions handle one board at a time")
    ws.ensure()
    ui.banner(ws)
    scan = update_manifest(ws)
    _warn_scan(scan)
    console.print(f"[muted]{len(scan.targets)} firmware target(s) found.[/muted]")

    def on_rescan(result: ScanResult) -> None:
        console.log(f"[muted]Firmware list updated: {len(result.targets)} target(s).[/muted]")

    try:
        from flashbot.firmware.watcher import start_sketch_watcher
        watcher = start_sketch_watcher(ws, on_rescan)
    except Exception as e:
        watcher = None
        console.print(f"[warn]Live sketch watching is unavailable: {escape(str(e))}[/warn]")

    events: "queue.Queue[tuple[float, PortInfo]]" = queue.Queue()
    start_listener(lambda info: events.put((time.time(), info)))
    for info in list_serial_ports():
        events.put((time.time(), info))

    session = Session(ws, auto=args.auto, sketch=args.sketch, run_tests=not args.no_test,
                      use_cache=not args.no_cache, jobs=args.jobs)
    mode = "interactive mode"
    if args.auto:
        mode = "unattended mode" + (f", up to {args.jobs} boards in parallel" if args.jobs > 1 else "")
    console.print(f"[muted]Waiting for boards ({mode}). Press Ctrl+C to exit.[/muted]")
    try:
        while True:
            try:
                event_time, info = events.get(timeout=0.5)
            except queue.Empty:
                continue
            session.handle(event_time, info)
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[muted]Stopped.[/muted]")
    finally:
        session.shutdown()
        if watcher:
            watcher.stop()
    return 0


# flash / build --------------------------------------------------------------

def _resolve_device(port: Optional[str], fqbn: Optional[str], yes: bool) -> DetectedDevice:
    if fqbn and not is_valid_fqbn(fqbn):
        raise UsageError(f"'{fqbn}' is not a valid FQBN (expected vendor:arch:board)")

    if port:
        info = find_port(port) or PortInfo(port=port, vid="", pid="")
        found = identify(info) if info.vid else None
    else:
        devices = connected_devices()
        known = [d for d in devices if isinstance(d, DetectedDevice)]
        candidates = known or (devices if fqbn else [])
        if not candidates:
            raise UsageError("No recognised board is connected. Connect one, or pass --port and --fqbn.")
        if len(candidates) > 1:
            if yes:
                raise UsageError("More than one board is connected; pass --port to choose one.")
            console.print("[bold]Select a board[/bold]")
            candidates = [candidates[ui.choose([f"{escape(getattr(d, 'name', 'Unrecognised board'))}  "
                                                f"[muted]{d.port}[/muted]" for d in candidates])]]
        found = candidates[0]
        info = PortInfo(found.port, found.vid, found.pid, found.serial_number)

    if fqbn:
        name = found.name if isinstance(found, DetectedDevice) else "Custom board"
        return DetectedDevice(port=info.port, name=name, fqbn=fqbn, vid=info.vid, pid=info.pid,
                              serial_number=info.serial_number,
                              pio_board=BoardInfo(name, fqbn).pio_board)
    if isinstance(found, DetectedDevice):
        return found
    raise UsageError(f"The board on {info.port} is not recognised. Pass --fqbn, or register it "
                     "with 'flashbot boards add'.")


def cmd_flash(args, ws: Workspace) -> int:
    device = _resolve_device(args.port, args.fqbn, args.yes)
    scan = discover(ws)
    targets = _filter(_resolve_targets(args.target, ws, scan), device.fqbn, args.env)
    targets = [t for t in targets if t.matches(device)]
    if not targets:
        detail = f"'{args.target}'" if args.target else "the workspace"
        raise UsageError(f"Nothing in {detail} targets {device.fqbn}. "
                         "Check the sketch folder, the PlatformIO board, or pass --env.")
    if len(targets) == 1 or args.yes:
        target = targets[0]
    else:
        target = ui.select_target(device, targets)
        if target is None:
            return 1

    ui.board_panel(device)
    result = _run_pipeline(device, target, ws, run_tests=not args.no_test, use_cache=not args.no_cache)
    _export(args, [export.from_pipeline(device, target, result)])
    return 0 if result.success else 1


def _export(args, records: list) -> None:
    if args.json:
        export.write_json(records, args.json)
        console.print(f"[muted]Wrote {args.json}[/muted]")
    if args.junit:
        export.write_junit(records, args.junit)
        console.print(f"[muted]Wrote {args.junit}[/muted]")


def cmd_build(args, ws: Workspace) -> int:
    scan = discover(ws)
    _warn_scan(scan)
    targets = _filter(_resolve_targets(args.target, ws, scan), args.fqbn, args.env)
    missing = [t for t in targets if t.kind == ARDUINO and not t.fqbn]
    if missing:
        raise UsageError(f"{missing[0].path} is outside sketches/; pass --fqbn to build it.")
    if not targets:
        if args.target or args.fqbn or args.env:
            raise UsageError("No firmware matches the given filters.")
        raise UsageError(f"No firmware found under {ws.sketches_dir}.")

    table = Table(title="Build results", box=box.SIMPLE_HEAVY, header_style="bold", title_justify="left")
    for col in ("Target", "Board", "Result"):
        table.add_column(col)
    failures = 0
    records = []
    for target in targets:
        console.print(f"\n[bold]{escape(target.label)}[/bold] [muted]({target.board_label})[/muted]")
        started = time.monotonic()
        try:
            step = get_flasher(target, ws, use_cache=False).build()
            error = step.error
        except (ToolNotFoundError, ValueError) as e:
            console.print(f"[err]{escape(str(e))}[/err]")
            step, error = None, str(e)
        ok = bool(step and step.ok)
        failures += not ok
        records.append(export.from_build(target, ok, None if ok else error or "Build failed",
                                         time.monotonic() - started))
        table.add_row(target.label, target.board_label,
                      Text("PASS", style="bold green") if ok else Text("FAIL", style="bold red"))
    console.print()
    console.print(table)
    _export(args, records)
    return 1 if failures else 0


# Inspection commands ------------------------------------------------------------

def cmd_devices(args, ws: Workspace) -> int:
    ports = list_serial_ports()
    if not ports:
        console.print("[warn]No USB serial devices found.[/warn]")
        return 0
    registry = BoardRegistry()
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    for col in ("Port", "USB ID", "Serial", "Board", "FQBN"):
        table.add_column(col, overflow="fold")
    for p in ports:
        found = identify(p, registry)
        if isinstance(found, DetectedDevice):
            board, fqbn = found.name, found.fqbn
        else:
            board, fqbn = Text("unrecognised", style="yellow"), Text(p.description, style="dim")
        table.add_row(p.port, f"{p.vid}:{p.pid}", p.serial_number or "-", board, fqbn)
    console.print(table)
    return 0


def cmd_sketches(args, ws: Workspace) -> int:
    scan = update_manifest(ws)
    _warn_scan(scan)
    if not scan.targets:
        console.print(f"[warn]No firmware found under {ws.sketches_dir}.[/warn]")
        return 0
    console.print(ui.targets_table(scan.targets))
    return 0


def cmd_boards(args, ws: Workspace) -> int:
    registry = BoardRegistry()
    action = args.action or "list"

    if action == "list":
        table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
        for col in ("USB ID", "Name", "FQBN", "PlatformIO", "Source"):
            table.add_column(col, overflow="fold")
        for vid, pid, info, source in registry.entries():
            if args.user and source != "user":
                continue
            table.add_row(f"{vid}:{pid}", info.name, info.fqbn, info.pio_board or "-",
                          Text(source, style="cyan" if source == "user" else "dim"))
        console.print(table)
        console.print(f"[muted]User registrations: {registry.path}[/muted]")
        return 0

    if action == "remove":
        vid, pid = _parse_usb_id(args.usb_id)
        if registry.remove(vid, pid):
            console.print(f"[ok]Removed[/ok] {vid}:{pid}")
            return 0
        raise UsageError(f"{vid}:{pid} is not a user registration (built-in boards cannot be removed)")

    # add
    if args.usb_id:
        vid, pid = _parse_usb_id(args.usb_id)
    else:
        unknown = [d for d in connected_devices(registry) if isinstance(d, UnknownBoard)]
        if not unknown:
            raise UsageError("No unrecognised board is connected. Pass the USB ID explicitly, e.g. 1a86:7523.")
        if len(unknown) > 1:
            console.print("[bold]Select a board[/bold]")
            unknown = [unknown[ui.choose([f"{u.vid}:{u.pid}  [muted]{u.port}[/muted]" for u in unknown])]]
        vid, pid = unknown[0].vid, unknown[0].pid

    if args.fqbn:
        if not is_valid_fqbn(args.fqbn):
            raise UsageError(f"'{args.fqbn}' is not a valid FQBN")
        info = BoardInfo(args.name or "My Board", args.fqbn, args.pio_board)
    else:
        suggested, fqbn = ui.select_board_type()
        info = BoardInfo(args.name or suggested or "My Board", fqbn, args.pio_board)
    registry.register(vid, pid, info)
    console.print(f"[ok]Registered[/ok] {vid}:{pid} as {escape(info.name)} ({info.fqbn})")
    return 0


def _parse_usb_id(value: str) -> tuple[str, str]:
    parts = value.lower().replace("0x", "").split(":")
    if len(parts) != 2 or not all(len(p) == 4 for p in parts):
        raise UsageError(f"'{value}' is not a USB ID; expected VID:PID such as 2341:0043")
    return parts[0], parts[1]


# Serial tools ----------------------------------------------------------------

def _port_and_baud(args) -> tuple[str, int]:
    port = args.port or guess_port()
    if not port:
        raise UsageError("No serial port found. Connect a board or pass the port explicitly.")
    return port, args.baud or ui.baud_rate()


def cmd_monitor(args, ws: Workspace) -> int:
    port, baud = _port_and_baud(args)
    SerialMonitor(port, baud, args.log).run()
    return 0


def cmd_plotter(args, ws: Workspace) -> int:
    port, baud = _port_and_baud(args)
    SerialPlotter(port, baud, args.history, args.labels).run()
    return 0


def cmd_report(args, ws: Workspace) -> int:
    print_report(limit=args.limit, failed_only=args.failed, days=args.days)
    return 0


def cmd_init(args, ws: Workspace) -> int:
    target = Workspace(Path(args.path).expanduser().resolve()) if args.path else ws
    target.ensure()
    console.print(f"[ok]Workspace ready[/ok] at {target.root}")
    console.print(f"  [muted]sketches[/muted]  {target.sketches_dir}")
    console.print(f"  [muted]config[/muted]    {target.config_dir}")
    console.print(f"  [muted]logs[/muted]      {target.logs_dir}")
    console.print("\nRun FlashBot from that directory, or set "
                  f"[info]FLASHBOT_HOME={target.root}[/info] to use it from anywhere.")
    return 0


def cmd_doctor(args, ws: Workspace) -> int:
    from flashbot.doctor import run_doctor
    return run_doctor(ws)


# Argument parsing -----------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flashbot",
        description="Detect, build, flash, and test microcontroller firmware.",
    )
    parser.add_argument("--version", action="version", version=f"FlashBot {__version__}")
    parser.add_argument("-w", "--workspace", metavar="DIR",
                        help="workspace directory (default: $FLASHBOT_HOME, ./ if it has sketches/, else ~/.flashbot)")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def report_flags(p):
        p.add_argument("--json", metavar="FILE", help="write results as JSON")
        p.add_argument("--junit", metavar="FILE", help="write results as JUnit XML")

    def pipeline_flags(p):
        p.add_argument("--no-test", action="store_true", help="skip post-flash serial tests")
        p.add_argument("--no-cache", action="store_true", help="always recompile, even if sources are unchanged")

    p = sub.add_parser("run", help="watch for boards and run the pipeline (default command)")
    p.add_argument("--auto", action="store_true",
                   help="unattended mode: no prompts, newest matching firmware, skip unknown boards")
    p.add_argument("--sketch", metavar="NAME", help="only flash the sketch or project with this name")
    p.add_argument("-j", "--jobs", type=int, default=1, metavar="N",
                   help="with --auto, flash up to N boards in parallel (default: 1)")
    pipeline_flags(p)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("flash", help="build, flash, and test one board, then exit")
    p.add_argument("target", nargs="?", help="sketch or project path, or a sketch name")
    p.add_argument("-p", "--port", help="serial port (default: the connected board)")
    p.add_argument("--fqbn", help="override the board FQBN")
    p.add_argument("-e", "--env", help="PlatformIO environment")
    p.add_argument("-y", "--yes", action="store_true", help="never prompt; pick the newest matching firmware")
    pipeline_flags(p)
    report_flags(p)
    p.set_defaults(func=cmd_flash)

    p = sub.add_parser("build", help="compile firmware without a board (all targets by default)")
    p.add_argument("target", nargs="?", help="sketch or project path, or a sketch name")
    p.add_argument("--fqbn", help="only build for this FQBN (required for sketches outside sketches/)")
    p.add_argument("-e", "--env", help="only build this PlatformIO environment")
    report_flags(p)
    p.set_defaults(func=cmd_build)

    sub.add_parser("devices", help="list connected serial devices").set_defaults(func=cmd_devices)
    sub.add_parser("sketches", help="list discovered firmware").set_defaults(func=cmd_sketches)

    p = sub.add_parser("boards", help="list, register, or remove boards")
    bsub = p.add_subparsers(dest="action", metavar="<action>")
    lp = bsub.add_parser("list", help="list known boards")
    lp.add_argument("--user", action="store_true", help="only show user registrations")
    ap = bsub.add_parser("add", help="register a board by USB ID")
    ap.add_argument("usb_id", nargs="?", help="VID:PID (default: the connected unrecognised board)")
    ap.add_argument("--name", help="display name")
    ap.add_argument("--fqbn", help="board FQBN (prompted if omitted)")
    ap.add_argument("--pio-board", help="PlatformIO board ID, if it cannot be inferred from the FQBN")
    rp = bsub.add_parser("remove", help="remove a user registration")
    rp.add_argument("usb_id", help="VID:PID")
    p.set_defaults(func=cmd_boards, user=False)

    p = sub.add_parser("monitor", help="open the serial monitor")
    p.add_argument("port", nargs="?", help="serial port (default: auto-detect)")
    p.add_argument("-b", "--baud", type=int, help="baud rate (prompted if omitted)")
    p.add_argument("-l", "--log", metavar="FILE", help="also write output to FILE")
    p.set_defaults(func=cmd_monitor)

    p = sub.add_parser("plotter", help="open the serial plotter")
    p.add_argument("port", nargs="?", help="serial port (default: auto-detect)")
    p.add_argument("-b", "--baud", type=int, help="baud rate (prompted if omitted)")
    p.add_argument("-n", "--history", type=int, default=80, help="samples kept per series (default: 80)")
    p.add_argument("--labels", nargs="+", default=[], metavar="NAME", help="names for unlabelled columns")
    p.set_defaults(func=cmd_plotter)

    p = sub.add_parser("report", help="show flash history")
    p.add_argument("-n", "--limit", type=int, default=25, help="number of runs to show (default: 25)")
    p.add_argument("--failed", action="store_true", help="only show failed runs")
    p.add_argument("--days", type=int, default=7, help="window for the failure summary (default: 7)")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("init", help="create a workspace")
    p.add_argument("path", nargs="?", help="directory to initialise (default: the active workspace)")
    p.set_defaults(func=cmd_init)

    sub.add_parser("doctor", help="check toolchains and system configuration").set_defaults(func=cmd_doctor)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args([*(argv if argv is not None else sys.argv[1:]), "run"])

    ws = resolve(args.workspace)
    set_workspace(ws)
    try:
        return args.func(args, get_workspace())
    except UsageError as e:
        console.print(f"[err]Error:[/err] {escape(str(e))}")
        return 2
    except ToolNotFoundError as e:
        console.print(f"[err]Error:[/err] {escape(str(e))}")
        return 2
    except KeyboardInterrupt:
        console.print("\n[muted]Cancelled.[/muted]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
