"""
Machine-readable results for CI systems: a JSON summary and JUnit XML.

Each run (one target on one board, or one build) becomes a JUnit test suite
whose test cases are the pipeline steps (build, upload) followed by the
post-flash tests, so CI dashboards show exactly which step failed.
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from flashbot import __version__


@dataclass
class StepRecord:
    name: str
    passed: bool
    detail: str = ""
    skipped: bool = False


@dataclass
class RunRecord:
    target: str
    path: str
    kind: str
    board: str
    fqbn: Optional[str]
    port: Optional[str]
    success: bool
    duration: float
    error: Optional[str] = None
    steps: list[StepRecord] = field(default_factory=list)


def from_build(target, ok: bool, error: Optional[str], duration: float) -> RunRecord:
    return RunRecord(
        target=target.label, path=target.path, kind=target.kind, board=target.board_label,
        fqbn=target.fqbn, port=None, success=ok, duration=round(duration, 2), error=error,
        steps=[StepRecord("build", ok, error or "")],
    )


def from_pipeline(device, target, result) -> RunRecord:
    steps = []
    failed = result.failed_stage
    if failed in ("idle", "detected"):
        steps.append(StepRecord("setup", False, result.error or ""))
    else:
        build_ok = failed != "building"
        detail = ("cached" if result.build_skipped else "") if build_ok else result.error or ""
        steps.append(StepRecord("build", build_ok, detail))
        if build_ok:
            steps.append(StepRecord("upload", result.flashed, "" if result.flashed else result.error or ""))
    if result.flashed:
        if result.tests_passed is None and failed != "testing":
            steps.append(StepRecord("tests", True, "skipped", skipped=True))
        elif not result.test_results:
            steps.append(StepRecord("tests", False, result.error or ""))
        for t in result.test_results:
            steps.append(StepRecord(f"test: {t.name}", t.passed, t.detail))
    return RunRecord(
        target=target.label, path=target.path, kind=target.kind, board=device.name,
        fqbn=device.fqbn, port=result.port or device.port, success=result.success,
        duration=round(result.duration, 2), error=result.error, steps=steps,
    )


def write_json(records: list[RunRecord], path: str) -> None:
    data = {
        "flashbot": __version__,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "runs": len(records),
            "passed": sum(r.success for r in records),
            "failed": sum(not r.success for r in records),
        },
        "runs": [asdict(r) for r in records],
    }
    _write(path, json.dumps(data, indent=2) + "\n")


def write_junit(records: list[RunRecord], path: str) -> None:
    root = ET.Element("testsuites", name="flashbot",
                      tests=str(sum(len(r.steps) for r in records)),
                      failures=str(sum(1 for r in records for s in r.steps if not s.passed)),
                      time=f"{sum(r.duration for r in records):.2f}")
    for r in records:
        suite = ET.SubElement(root, "testsuite", name=f"{r.target} ({r.board})",
                              tests=str(len(r.steps)),
                              failures=str(sum(not s.passed for s in r.steps)),
                              skipped=str(sum(s.skipped and s.passed for s in r.steps)),
                              time=f"{r.duration:.2f}")
        props = ET.SubElement(suite, "properties")
        for key, value in (("path", r.path), ("kind", r.kind), ("fqbn", r.fqbn), ("port", r.port)):
            if value:
                ET.SubElement(props, "property", name=key, value=value)
        for step in r.steps:
            case = ET.SubElement(suite, "testcase", classname=r.target, name=step.name)
            if not step.passed:
                failure = ET.SubElement(case, "failure", message=step.detail or "failed")
                failure.text = step.detail
            elif step.skipped:
                ET.SubElement(case, "skipped", message=step.detail or "skipped")
    ET.indent(root)
    _write(path, ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n")


def _write(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
