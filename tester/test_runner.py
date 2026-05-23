"""
Runs test cases over serial after flashing.
Uses tester/serial_comm.py for all port I/O.
"""

from tester.serial_comm import SerialComm
from tester.test_cases import TestCase


class TestRunner:
    def __init__(self, port: str, baudrate: int = 9600):
        self.comm = SerialComm(port, baud=baudrate, timeout=2.0)

    def run_test(self, test_case: TestCase):
        if not self.comm.is_connected():
            raise RuntimeError("Serial port not open")

        if test_case.command:
            response = self.comm.send(test_case.command)
        else:
            response = ""

        if test_case.expected_response:
            passed = test_case.expected_response in response
        else:
            passed = True

        return passed, response

    def run_all(self, test_cases: list[TestCase]):
        results = []
        all_passed = True

        with self.comm:
            for tc in test_cases:
                try:
                    passed, response = self.run_test(tc)
                    results.append({
                        "name": tc.name,
                        "passed": passed,
                        "response": response
                    })
                    if not passed:
                        all_passed = False
                except Exception as e:
                    results.append({
                        "name": tc.name,
                        "passed": False,
                        "response": str(e)
                    })
                    all_passed = False

        return all_passed, results