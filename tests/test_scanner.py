from conftest import write

from flashbot.detector.device_id import DetectedDevice
from flashbot.firmware.scanner import discover, fqbn_from_parts, targets_for_device, targets_in, update_manifest
from flashbot.firmware.targets import ARDUINO, PLATFORMIO


def test_fqbn_from_parts():
    assert fqbn_from_parts(["arduino", "avr", "uno"]) == "arduino:avr:uno"
    assert fqbn_from_parts(["arduino", "avr", "nano", "cpu=atmega328old"]) == "arduino:avr:nano:cpu=atmega328old"
    assert fqbn_from_parts(["esp32", "esp32", "esp32s3", "PSRAM=opi", "FlashSize=16M"]) == \
        "esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M"
    assert fqbn_from_parts(["arduino", "avr"]) is None
    assert fqbn_from_parts(["arduino", "avr", "uno", "extra"]) is None


def test_discovers_arduino_sketches_including_fqbn_options(ws):
    write(ws.sketches_dir / "arduino/avr/uno/blink/blink.ino")
    write(ws.sketches_dir / "arduino/avr/nano/cpu=atmega328old/imu/imu.ino")
    result = discover(ws)
    assert {(t.name, t.fqbn) for t in result.targets} == {
        ("blink", "arduino:avr:uno"),
        ("imu", "arduino:avr:nano:cpu=atmega328old"),
    }
    assert all(t.kind == ARDUINO for t in result.targets)
    assert result.warnings == []


def test_discovers_platformio_environments(ws):
    write(ws.sketches_dir / "pio/demo/platformio.ini",
          "[env]\nframework = arduino\nmonitor_speed = 115200\n"
          "[env:esp32dev]\nplatform = espressif32\nboard = esp32dev\n"
          "[env:uno]\nplatform = atmelavr\nboard = uno\nmonitor_speed = 9600\n")
    write(ws.sketches_dir / "pio/demo/src/main.cpp")
    targets = {t.env: t for t in discover(ws).targets}
    assert set(targets) == {"esp32dev", "uno"}
    assert targets["esp32dev"].kind == PLATFORMIO
    assert targets["esp32dev"].baud == 115200
    assert targets["uno"].baud == 9600


def test_reports_misplaced_sketches(ws):
    write(ws.sketches_dir / "arduino/avr/uno/blink/other_name.ino")
    write(ws.sketches_dir / "too/short/blink/blink.ino")
    result = discover(ws)
    assert result.targets == []
    assert len(result.warnings) == 2


def test_targets_for_device_matches_fqbn_and_platformio_board(ws):
    write(ws.sketches_dir / "esp32/esp32/esp32/blink/blink.ino")
    write(ws.sketches_dir / "arduino/avr/uno/blink/blink.ino")
    write(ws.sketches_dir / "pio/demo/platformio.ini", "[env:dev]\nboard = esp32dev\n")
    device = DetectedDevice(port="/dev/ttyUSB0", name="ESP32", fqbn="esp32:esp32:esp32",
                            vid="10c4", pid="ea60", pio_board="esp32dev")
    matched = targets_for_device(device, discover(ws).targets)
    assert sorted(t.label for t in matched) == ["blink", "demo [dev]"]


def test_targets_in_outside_workspace_has_no_fqbn(ws, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / "probe"
    write(outside / "probe.ino")
    (target,) = targets_in(outside, ws).targets
    assert target.fqbn is None and target.path == outside.as_posix()


def test_manifest_is_written(ws):
    write(ws.sketches_dir / "arduino/avr/uno/blink/blink.ino")
    update_manifest(ws)
    assert '"arduino:avr:uno"' in ws.manifest_path.read_text()
