import pytest
from conftest import write

from flashbot.firmware.spec import read_spec, required_libraries


def test_missing_spec_is_empty(tmp_path):
    assert read_spec(tmp_path) == {}
    assert required_libraries(tmp_path) == []


def test_libraries(tmp_path):
    write(tmp_path / "flashbot.json", '{"libraries": ["Servo", " Adafruit BMP280 Library@2.6.8 "]}')
    assert required_libraries(tmp_path) == ["Servo", "Adafruit BMP280 Library@2.6.8"]


@pytest.mark.parametrize("content", ['[]', '{"libraries": "Servo"}', '{"libraries": [""]}', '{"libraries": [3]}'])
def test_invalid_libraries(tmp_path, content):
    write(tmp_path / "flashbot.json", content)
    with pytest.raises(ValueError):
        read_spec(tmp_path)
