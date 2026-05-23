"""
Test case definitions for post-flash serial validation.
"""

class TestCase:
    def __init__(self, name, command, expected_response, timeout=2):
        self.name = name
        self.command = command
        self.expected_response = expected_response
        self.timeout = timeout

    def __repr__(self):
        return f"TestCase({self.name})"


def get_tests_for_sketch(sketch_path: str):
    """
    Returns a list of TestCases appropriate for the given sketch.
    """
    sketch_name = sketch_path.lower()

    if "blink" in sketch_name:
        return [
            TestCase("board_boots", "", "", timeout=3),
        ]
    elif "echo" in sketch_name or "serial" in sketch_name:
        return [
            TestCase("echo_hello", "HELLO", "HELLO", timeout=2),
            TestCase("echo_number", "12345", "12345", timeout=2),
        ]
    else:
        return [
            TestCase("serial_alive", "", "", timeout=3),
        ]