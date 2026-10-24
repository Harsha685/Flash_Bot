import json

import pytest
from conftest import write

from flashbot.tester.test_cases import DEFAULT_BAUD, detect_baud, load_suite


def test_default_suite_detects_baud_from_source(tmp_path):
    write(tmp_path / "s.ino", "void setup() { Serial.begin(115200); }")
    suite = load_suite(tmp_path)
    assert suite.baud == 115200
    assert [t.name for t in suite.tests] == ["port_opens"]
    assert suite.source == "default"


def test_platformio_sources_and_declared_baud(tmp_path):
    write(tmp_path / "src/main.cpp", "Serial1.begin(57600);")
    assert detect_baud(tmp_path) == 57600
    assert load_suite(tmp_path, declared_baud=9600).baud == 9600
    assert load_suite(tmp_path / "missing").baud == DEFAULT_BAUD


def test_spec_file(tmp_path):
    write(tmp_path / "flashbot.json", json.dumps({
        "baud": 38400, "boot_delay": 0.5,
        "tests": [{"name": "ping", "send": "PING", "expect": "PONG"},
                  {"expect": "^v\\d+", "regex": True, "timeout": 4}],
    }))
    suite = load_suite(tmp_path)
    assert suite.baud == 38400 and suite.boot_delay == 0.5
    assert suite.tests[0].send == "PING"
    assert suite.tests[1].name == "test_2" and suite.tests[1].regex and suite.tests[1].timeout == 4


@pytest.mark.parametrize("content", ["{bad", '{"tests": {}}', '{"tests": [{"expect": "(", "regex": true}]}'])
def test_invalid_spec_raises(tmp_path, content):
    write(tmp_path / "flashbot.json", content)
    with pytest.raises(ValueError):
        load_suite(tmp_path)
