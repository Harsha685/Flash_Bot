import threading

from flashbot.console import get_prefix, output_prefix
from flashbot.detector.device_id import PortInfo
from flashbot.flasher.base import build_lock, summarize_error


def test_device_keys_distinguish_serialless_boards():
    a = PortInfo("/dev/ttyUSB0", "1a86", "7523")
    b = PortInfo("/dev/ttyUSB1", "1a86", "7523")
    assert a.key != b.key
    moved = PortInfo("/dev/ttyACM1", "2341", "1002", "SN1")
    assert moved.key == PortInfo("/dev/ttyACM0", "2341", "1002", "SN1").key


def test_build_lock_is_shared_per_key():
    assert build_lock("build/x") is build_lock("build/x")
    assert build_lock("build/x") is not build_lock("build/y")


def test_output_prefix_is_per_thread():
    seen = {}

    def worker():
        with output_prefix("ttyUSB0"):
            seen["worker"] = get_prefix()

    with output_prefix("main"):
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        seen["main"] = get_prefix()
    assert seen == {"worker": "ttyUSB0", "main": "main"}
    assert get_prefix() == ""


def test_summarize_error_prefers_error_lines():
    assert summarize_error("Sketch uses 10 bytes\nError: port busy\nmore") == "Error: port busy"
    assert summarize_error("line one\nlast line") == "last line"
    assert summarize_error("") == ""
