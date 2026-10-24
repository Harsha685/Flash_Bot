import json
import xml.etree.ElementTree as ET

from flashbot.detector.device_id import DetectedDevice
from flashbot.firmware.targets import FirmwareTarget
from flashbot.logger import export
from flashbot.pipeline.state_machine import PipelineResult
from flashbot.tester.test_runner import TestResult

DEVICE = DetectedDevice(port="/dev/ttyACM0", name="Uno", fqbn="arduino:avr:uno", vid="2341", pid="0043")
TARGET = FirmwareTarget(kind="arduino", name="blink", path="sketches/arduino/avr/uno/blink", fqbn="arduino:avr:uno")


def steps(result):
    return [(s.name, s.passed) for s in export.from_pipeline(DEVICE, TARGET, result).steps]


def test_pipeline_steps_for_each_outcome():
    assert steps(PipelineResult(success=False, failed_stage="building", error="Build failed: x")) == [("build", False)]
    assert steps(PipelineResult(success=False, failed_stage="flashing", error="Upload failed")) == \
        [("build", True), ("upload", False)]
    assert steps(PipelineResult(success=False, failed_stage="detected", error="arduino-cli missing")) == \
        [("setup", False)]
    tested = PipelineResult(success=False, flashed=True, failed_stage="testing", tests_passed=False,
                            test_results=[TestResult("ping", True, "PONG"), TestResult("led", False, "no")])
    assert steps(tested) == [("build", True), ("upload", True), ("test: ping", True), ("test: led", False)]
    lost = PipelineResult(success=False, flashed=True, failed_stage="testing", error="did not reappear")
    assert steps(lost)[-1] == ("tests", False)


def test_json_and_junit(tmp_path):
    ok = export.from_pipeline(DEVICE, TARGET, PipelineResult(success=True, flashed=True, duration=3.0))
    bad = export.from_build(TARGET, False, "Build failed: boom", 1.5)
    export.write_json([ok, bad], tmp_path / "r.json")
    export.write_junit([ok, bad], tmp_path / "out/r.xml")

    data = json.loads((tmp_path / "r.json").read_text())
    assert data["summary"] == {"runs": 2, "passed": 1, "failed": 1}

    root = ET.parse(tmp_path / "out/r.xml").getroot()
    assert root.get("failures") == "1"
    suites = root.findall("testsuite")
    assert suites[0].find("testcase[@name='tests']/skipped") is not None
    assert suites[1].find("testcase/failure").get("message") == "Build failed: boom"
