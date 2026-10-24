"""
Orchestrates one pipeline run: build, flash, test, and record the outcome.

    IDLE -> DETECTED -> BUILDING -> FLASHING -> TESTING -> DONE
                           |           |           |
                           +-----------+-----------+--> FAILED

The flasher, port waiter, and test runner are injectable so the state
machine can be exercised without hardware.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from flashbot.detector.device_id import DetectedDevice, wait_for_port
from flashbot.firmware.targets import FirmwareTarget
from flashbot.flasher import get_flasher
from flashbot.logger.result_store import save_result
from flashbot.tester.test_cases import load_suite
from flashbot.tester.test_runner import TestResult, TestRunner
from flashbot.workspace import Workspace, get_workspace


class PipelineState(Enum):
    IDLE = "idle"
    DETECTED = "detected"
    BUILDING = "building"
    FLASHING = "flashing"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"


TRANSITIONS = {
    PipelineState.IDLE:     [PipelineState.DETECTED],
    PipelineState.DETECTED: [PipelineState.BUILDING, PipelineState.FAILED],
    PipelineState.BUILDING: [PipelineState.FLASHING, PipelineState.FAILED],
    PipelineState.FLASHING: [PipelineState.TESTING, PipelineState.DONE, PipelineState.FAILED],
    PipelineState.TESTING:  [PipelineState.DONE, PipelineState.FAILED],
    PipelineState.DONE:     [PipelineState.IDLE],
    PipelineState.FAILED:   [PipelineState.IDLE],
}


@dataclass
class PipelineResult:
    success: bool = False
    flashed: bool = False
    build_skipped: bool = False
    failed_stage: Optional[str] = None
    error: Optional[str] = None
    tests_passed: Optional[bool] = None       # None when tests were skipped
    test_results: list[TestResult] = field(default_factory=list)
    port: str = ""                            # port after re-enumeration
    baud: Optional[int] = None
    source_hash: Optional[str] = None         # set once the build succeeds
    duration: float = 0.0


class PipelineStateMachine:
    def __init__(self, on_state_change: Optional[Callable] = None,
                 on_test_result: Optional[Callable] = None,
                 workspace: Optional[Workspace] = None,
                 run_tests: bool = True, use_cache: bool = True,
                 flasher_factory: Callable = get_flasher,
                 port_waiter: Callable = wait_for_port,
                 runner_factory: Callable = TestRunner,
                 record: bool = True):
        self.state = PipelineState.IDLE
        self.on_state_change = on_state_change or (lambda old, new: None)
        self.on_test_result = on_test_result or (lambda passed, results: None)
        self.ws = workspace or get_workspace()
        self.run_tests = run_tests
        self.use_cache = use_cache
        self.flasher_factory = flasher_factory
        self.port_waiter = port_waiter
        self.runner_factory = runner_factory
        self.record = record

    def transition(self, new_state: PipelineState) -> None:
        if new_state not in TRANSITIONS.get(self.state, []):
            raise RuntimeError(f"Illegal transition: {self.state.value} -> {new_state.value}")
        old, self.state = self.state, new_state
        self.on_state_change(old, new_state)

    def _fail(self, result: PipelineResult, error: str) -> None:
        result.failed_stage = self.state.value
        result.error = error
        if PipelineState.FAILED in TRANSITIONS.get(self.state, []):
            self.transition(PipelineState.FAILED)
        else:
            self.state = PipelineState.FAILED

    def run(self, device: DetectedDevice, target: FirmwareTarget) -> PipelineResult:
        result = PipelineResult(port=device.port)
        started = time.monotonic()
        try:
            self._execute(device, target, result)
        except KeyboardInterrupt:
            self._fail(result, "Interrupted")
            raise
        except Exception as e:  # tool missing, bad spec file, serial errors, ...
            self._fail(result, str(e))
        finally:
            result.duration = time.monotonic() - started
            if self.record:
                self._save(device, target, result)
            self.state = PipelineState.IDLE
        return result

    def _execute(self, device: DetectedDevice, target: FirmwareTarget,
                 result: PipelineResult) -> None:
        self.transition(PipelineState.DETECTED)
        flasher = self.flasher_factory(target, self.ws, self.use_cache)

        self.transition(PipelineState.BUILDING)
        build = flasher.build()
        if not build.ok:
            self._fail(result, build.error or "Build failed")
            return
        result.build_skipped = build.skipped
        result.source_hash = build.source_hash

        self.transition(PipelineState.FLASHING)
        flash = flasher.flash(device.port)
        if not flash.ok:
            self._fail(result, flash.error or "Upload failed")
            return
        result.flashed = True

        if not self.run_tests:
            self.transition(PipelineState.DONE)
            result.success = True
            return

        self.transition(PipelineState.TESTING)
        suite = load_suite(self.ws.abspath(target.path), declared_baud=target.baud)
        result.baud = suite.baud
        port = self.port_waiter(device)
        if not port:
            self._fail(result, f"{device.name} did not reappear after upload")
            return
        result.port = port

        passed, results = self.runner_factory(port, suite).run()
        result.tests_passed, result.test_results = passed, results
        self.on_test_result(passed, results)
        if not passed:
            failed = ", ".join(r.name for r in results if not r.passed)
            self._fail(result, f"Tests failed: {failed}")
            return

        self.transition(PipelineState.DONE)
        result.success = True

    def _save(self, device, target, result: PipelineResult) -> None:
        if result.tests_passed is None:
            test_status = "skipped" if result.flashed else None
        else:
            test_status = "passed" if result.tests_passed else "failed"
        save_result(
            board_name=device.name,
            fqbn=device.fqbn,
            port=result.port or device.port,
            sketch_path=target.path,
            status="success" if result.success else "failed",
            error=result.error,
            source_hash=result.source_hash,
            target_kind=target.kind,
            env=target.env,
            stage=result.failed_stage or "done",
            test_status=test_status,
            duration=round(result.duration, 2),
        )
