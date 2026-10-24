from flashbot.tools.serial_plotter import parse_line, sparkline


def test_labelled_values():
    assert parse_line("temp: 24.5, hum=60") == {"temp": 24.5, "hum": 60.0}
    assert parse_line("t:-1.5e2") == {"t": -150.0}


def test_bare_columns_use_labels_then_channel_names():
    assert parse_line("1,2\t3 4", ["a", "b"]) == {"a": 1.0, "b": 2.0, "Ch2": 3.0, "Ch3": 4.0}
    assert parse_line(".5") == {"Ch0": 0.5}


def test_non_numeric_lines_are_ignored():
    assert parse_line("Booting...") == {}
    assert parse_line("") == {}


def test_sparkline_spans_full_range():
    assert sparkline([0, 5, 10], 0, 10) == " ▄█"
    assert sparkline([3, 3], 3, 3) == "  "
