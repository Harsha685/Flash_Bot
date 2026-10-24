"""Runs a TestSuite against a freshly flashed board."""

from dataclasses import dataclass

from flashbot.tester.serial_comm import SerialComm
from flashbot.tester.test_cases import TestCase, TestSuite


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class

    name: str
    passed: bool
    detail: str = ""


class TestRunner:
    __test__ = False

    def __init__(self, port: str, suite: TestSuite):
        self.suite = suite
        self.comm = SerialComm(port, baud=suite.baud)

    def _run_one(self, tc: TestCase) -> TestResult:
        if not tc.send and not tc.expect:
            return TestResult(tc.name, True, "port opened")
        if tc.send:
            matched, lines = self.comm.transact(tc.send, tc.expect, tc.timeout, tc.regex)
        else:
            matched, lines = self.comm.read_until(tc.expect, tc.timeout, tc.regex)
        if matched:
            return TestResult(tc.name, True, lines[-1] if lines else "")
        if tc.expect:
            got = lines[-1] if lines else "no output"
            return TestResult(tc.name, False, f"expected '{tc.expect}', got: {got}")
        return TestResult(tc.name, False, "no response")

    def run(self) -> tuple[bool, list[TestResult]]:
        try:
            self.comm.connect(boot_delay=self.suite.boot_delay)
        except ConnectionError as e:
            return False, [TestResult(tc.name, False, str(e)) for tc in self.suite.tests]

        results = []
        try:
            for tc in self.suite.tests:
                try:
                    results.append(self._run_one(tc))
                except Exception as e:
                    results.append(TestResult(tc.name, False, str(e)))
        finally:
            self.comm.disconnect()
        return all(r.passed for r in results), results
