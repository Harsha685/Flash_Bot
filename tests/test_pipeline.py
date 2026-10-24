from conftest import write

from flashbot.detector.device_id import DetectedDevice
from flashbot.firmware.targets import FirmwareTarget
from flashbot.flasher.base import StepResult
from flashbot.logger.result_store import get_last_build_hash, get_results
from flashbot.pipeline.state_machine import PipelineState, PipelineStateMachine
from flashbot.tester.test_runner import TestResult

DEVICE = DetectedDevice(port="/dev/ttyACM0", name="Uno", fqbn="arduino:avr:uno", vid="2341", pid="0043")
TARGET = FirmwareTarget(kind="arduino", name="blink", path="sketches/arduino/avr/uno/blink", fqbn="arduino:avr:uno")


class FakeFlasher:
    def __init__(self, build_ok=True, flash_ok=True):
        self.build_ok, self.flash_ok = build_ok, flash_ok
        self.flashed_to = None

    def build(self):
        return StepResult(ok=self.build_ok, error=None if self.build_ok else "Build failed",
                          source_hash="abc123" if self.build_ok else None)

    def flash(self, port):
        self.flashed_to = port
        return StepResult(ok=self.flash_ok, error=None if self.flash_ok else "Upload failed")


class FakeRunner:
    def __init__(self, passed):
        self.passed = passed

    def __call__(self, port, suite):
        return self

    def run(self):
        return self.passed, [TestResult("port_opens", self.passed, "")]


def machine(ws, flasher, passed=True, port="/dev/ttyACM1", **kw):
    states = []
    m = PipelineStateMachine(
        on_state_change=lambda old, new: states.append(new), workspace=ws,
        flasher_factory=lambda target, ws, cache: flasher,
        port_waiter=lambda device: port, runner_factory=FakeRunner(passed), **kw,
    )
    return m, states


def test_success_records_hash_and_new_port(ws):
    write(ws.root / TARGET.path / "blink.ino")
    m, states = machine(ws, FakeFlasher())
    result = m.run(DEVICE, TARGET)
    assert result.success and result.port == "/dev/ttyACM1"
    assert states[-1] == PipelineState.DONE and m.state == PipelineState.IDLE
    row = get_results()[0]
    assert (row["status"], row["test_status"], row["stage"]) == ("success", "passed", "done")
    assert get_last_build_hash("arduino:avr:uno", TARGET.path) == "abc123"


def test_build_failure_stops_before_flashing(ws):
    flasher = FakeFlasher(build_ok=False)
    m, states = machine(ws, flasher)
    result = m.run(DEVICE, TARGET)
    assert not result.success and result.failed_stage == "building"
    assert flasher.flashed_to is None
    assert PipelineState.FLASHING not in states
    assert get_results()[0]["source_hash"] is None


def test_upload_failure_keeps_build_hash(ws):
    m, _ = machine(ws, FakeFlasher(flash_ok=False))
    result = m.run(DEVICE, TARGET)
    assert result.failed_stage == "flashing" and not result.flashed
    assert get_last_build_hash("arduino:avr:uno", TARGET.path) == "abc123"


def test_failed_tests_fail_the_run(ws):
    write(ws.root / TARGET.path / "blink.ino")
    m, states = machine(ws, FakeFlasher(), passed=False)
    result = m.run(DEVICE, TARGET)
    assert result.flashed and not result.success
    assert result.error == "Tests failed: port_opens"
    assert states[-1] == PipelineState.FAILED
    assert get_results()[0]["test_status"] == "failed"


def test_board_that_never_returns_fails_testing(ws):
    write(ws.root / TARGET.path / "blink.ino")
    m, _ = machine(ws, FakeFlasher(), port=None)
    result = m.run(DEVICE, TARGET)
    assert result.failed_stage == "testing" and "did not reappear" in result.error


def test_tests_can_be_skipped(ws):
    m, states = machine(ws, FakeFlasher(), run_tests=False)
    result = m.run(DEVICE, TARGET)
    assert result.success and result.tests_passed is None
    assert PipelineState.TESTING not in states
    assert get_results()[0]["test_status"] == "skipped"


def test_unexpected_exception_is_recorded(ws):
    def boom(*_):
        raise RuntimeError("arduino-cli exploded")
    m = PipelineStateMachine(workspace=ws, flasher_factory=boom)
    result = m.run(DEVICE, TARGET)
    assert not result.success and result.error == "arduino-cli exploded"
    assert get_results()[0]["error"] == "arduino-cli exploded"
