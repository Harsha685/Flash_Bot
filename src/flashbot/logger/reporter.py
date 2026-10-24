"""Renders flash history from the result store."""

from datetime import datetime, timedelta
from pathlib import PurePosixPath

from rich import box
from rich.table import Table
from rich.text import Text

from flashbot.console import console
from flashbot.logger.result_store import get_results, get_stats


def _target_name(path: str) -> str:
    """Sketch or project name; older rows stored the .ino file rather than its folder."""
    p = PurePosixPath(path)
    return p.parent.name if p.suffix == ".ino" else p.name


def _status(row) -> Text:
    if row["status"] == "success":
        return Text("PASS", style="bold green")
    return Text("FAIL", style="bold red")


def _tests(row) -> str:
    return {"passed": "passed", "failed": "failed", "skipped": "skipped"}.get(row["test_status"] or "", "-")


def print_report(limit: int = 25, failed_only: bool = False, days: int = 7) -> None:
    rows = get_results(limit=limit, failed_only=failed_only)
    if not rows:
        console.print("[warn]No runs recorded yet.[/warn]")
        return

    table = Table(title="Flash History", box=box.SIMPLE_HEAVY, header_style="bold", title_justify="left")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Timestamp", style="dim", no_wrap=True)
    table.add_column("Board")
    table.add_column("Target")
    table.add_column("Result", justify="center")
    table.add_column("Tests", justify="center")
    table.add_column("Error", overflow="fold", style="red")

    for row in rows:
        target = _target_name(row["sketch_path"])
        if row["env"]:
            target += f" [{row['env']}]"
        table.add_row(
            str(row["id"]), row["timestamp"], Text(row["board_name"]), Text(target),
            _status(row), _tests(row), Text(row["error"] or ""),
        )
    console.print(table)

    stats = get_stats()
    recent_failures = len(get_results(failed_only=True, since=datetime.now() - timedelta(days=days)))
    console.print(
        f"[muted]{stats['total']} runs recorded: {stats['success']} passed, {stats['failed']} failed. "
        f"{recent_failures} failure(s) in the last {days} days.[/muted]"
    )
