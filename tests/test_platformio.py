from conftest import write

from flashbot.firmware.platformio import parse_platformio_ini


def test_inheritance_extends_and_custom_fqbn(tmp_path):
    ini = write(tmp_path / "platformio.ini", """
[env]
framework = arduino
monitor_speed = 115200   ; inline comment

[common_esp]
platform = espressif32

[env:base]
extends = common_esp
board = esp32dev

[env:custom]
extends = env:base
board = my_board
custom_flashbot_fqbn = esp32:esp32:esp32s3
monitor_speed = ${env.monitor_speed}
""")
    envs = {e.name: e for e in parse_platformio_ini(ini)}
    assert envs["base"].platform == "espressif32"
    assert envs["base"].framework == "arduino"
    assert envs["base"].monitor_speed == 115200
    assert envs["custom"].board == "my_board"
    assert envs["custom"].fqbn == "esp32:esp32:esp32s3"
    assert envs["custom"].monitor_speed is None  # interpolated values are not evaluated
