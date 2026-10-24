import json

from flashbot.detector.boards import BUILTIN_BOARDS, BoardInfo, BoardRegistry, is_valid_fqbn
from flashbot.detector.device_id import DetectedDevice, PortInfo, UnknownBoard, identify


def test_user_registration_overrides_builtin_and_persists_only_user_entries(ws):
    registry = BoardRegistry()
    registry.register("1A86", "7523", BoardInfo("Nano clone", "arduino:avr:nano:cpu=atmega328old"))

    saved = json.loads(ws.user_boards_path.read_text())
    assert list(saved) == ["1a86:7523"]
    assert "pio_board" not in saved["1a86:7523"]  # inferred from the FQBN, so not written

    reloaded = BoardRegistry()
    assert reloaded.lookup("1a86", "7523").name == "Nano clone"
    assert reloaded.lookup("1a86", "7523").pio_board == "nanoatmega328"
    assert reloaded.remove("1a86", "7523")
    assert reloaded.lookup("1a86", "7523") == BUILTIN_BOARDS[("1a86", "7523")]
    assert not reloaded.remove("2341", "0043")  # built-ins cannot be removed


def test_identify(ws):
    registry = BoardRegistry()
    known = identify(PortInfo("/dev/ttyACM0", "2341", "1002", "ABC"), registry)
    assert isinstance(known, DetectedDevice) and known.fqbn == "arduino:renesas_uno:unor4wifi"
    assert known.pio_board == "uno_r4_wifi"
    assert isinstance(identify(PortInfo("/dev/ttyUSB0", "dead", "beef"), registry), UnknownBoard)
    assert identify(PortInfo("/dev/ttyS0", "8086", "0001"), registry) is None


def test_corrupt_user_file_is_ignored(ws):
    ws.user_boards_path.write_text("{not json")
    assert BoardRegistry().user == {}


def test_is_valid_fqbn():
    assert is_valid_fqbn("arduino:avr:uno")
    assert is_valid_fqbn("arduino:avr:nano:cpu=atmega328old")
    assert not is_valid_fqbn("arduino:avr")
    assert not is_valid_fqbn("arduino::uno")
