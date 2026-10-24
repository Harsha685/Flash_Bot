# FlashBot

FlashBot is a command-line tool that automates the firmware workflow for microcontroller boards. Connect a board and FlashBot identifies it, selects matching firmware, builds it with arduino-cli or PlatformIO, uploads it, verifies it over the serial port, and records the result.

[![CI](https://github.com/Harsha685/Flash_Bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Harsha685/Flash_Bot/actions/workflows/ci.yml)

**Version 0.3.0** | [Documentation](https://harsha685.github.io/Flash_Bot/) | [Changelog](CHANGELOG.md) | [Contributing](CONTRIBUTING.md)

---

## Contents

- [Overview](#overview)
- [Supported hardware](#supported-hardware)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Workspace layout](#workspace-layout)
- [Command reference](#command-reference)
- [Sketch settings and tests](#sketch-settings-and-tests)
- [Board registration](#board-registration)
- [Unattended operation](#unattended-operation)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

A typical manual cycle (open the IDE, select the board and port, compile, upload, open the serial monitor, check the output) is repeated many times a day during firmware development and in lab or production settings. FlashBot reduces it to connecting the board.

| Stage | What FlashBot does |
|-------|--------------------|
| Detect | Listens for USB hotplug events (udev on Linux, polling elsewhere) and reads the USB vendor and product IDs. |
| Identify | Maps the USB ID to a board name, FQBN, and PlatformIO board ID. Unrecognised boards can be registered once and are remembered. |
| Select | Finds every Arduino sketch and PlatformIO environment in the workspace that targets the detected board. |
| Build | Compiles with arduino-cli or PlatformIO. Arduino builds are skipped when the sources are unchanged since the last successful build. |
| Flash | Uploads to the board, retrying where the platform benefits from it (ESP32). |
| Test | Waits for the board to re-enumerate, then runs the serial test suite declared in the sketch's `flashbot.json`. |
| Record | Writes every run, including failures and the failing stage, to a local SQLite database. |

After a successful interactive run, FlashBot offers the built-in serial monitor or serial plotter.

---

## Supported hardware

Any board supported by an installed arduino-cli core or a PlatformIO platform can be built and flashed. The boards below are identified automatically from their USB ID; others are registered once through a guided prompt.

| Family | Boards recognised automatically | Toolchain |
|--------|---------------------------------|-----------|
| Arduino AVR | Uno, Mega 2560, Leonardo, Micro | arduino-cli, PlatformIO |
| Arduino megaAVR / SAMD | Nano Every, Nano 33 IoT | arduino-cli, PlatformIO |
| Arduino Renesas | Uno R4 WiFi, Uno R4 Minima | arduino-cli, PlatformIO |
| Espressif | ESP32 (CP210x and CH340 bridges), ESP32-S2, ESP32-S3, ESP32-C3 | arduino-cli, PlatformIO |
| Raspberry Pi | Pico, Pico W (arduino-pico core) | arduino-cli, PlatformIO |
| PJRC Teensy | Teensy 4.0, 4.1 (via registration) | arduino-cli, PlatformIO |
| STMicroelectronics | Nucleo-F401RE, Nucleo-F446RE, Blue Pill (via registration) | arduino-cli, PlatformIO |

Generic USB-serial bridges (CP210x, CH340, FTDI) are shared by many boards. If a bridge is mapped to the wrong board, register the correct one; user registrations take precedence over the built-in table.

---

## Requirements

- Python 3.10 or later
- Linux (primary platform; uses udev for hotplug detection). Other platforms fall back to polling and are untested.
- [arduino-cli](https://arduino.github.io/arduino-cli/latest/installation/) for Arduino sketches
- [PlatformIO Core](https://docs.platformio.org/en/latest/core/installation/) for PlatformIO projects (optional)
- Membership in the `dialout` group for serial port access

---

## Installation

```bash
git clone https://github.com/Harsha685/Flash_Bot.git
cd Flash_Bot
```

With Poetry:

```bash
poetry install
poetry run flashbot --version
```

With pip (installs the `flashbot` command into the active environment):

```bash
pip install .
flashbot --version
```

Install the arduino-cli cores for your boards:

```bash
arduino-cli config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json \
  https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
arduino-cli core update-index
arduino-cli core install arduino:avr arduino:renesas_uno esp32:esp32 rp2040:rp2040
```

Then confirm that the environment is ready:

```bash
flashbot doctor
```

---

## Quick start

From the repository root, which already contains example sketches:

```bash
flashbot
```

Connect a board. FlashBot prints what it found, lists the matching firmware, and runs the pipeline for the selected entry:

```
╭─ Arduino Uno R4 WiFi ──────────────────────────────╮
│ Port         /dev/ttyACM0                          │
│ FQBN         arduino:renesas_uno:unor4wifi         │
│ USB ID       2341:1002                             │
│ PlatformIO   uno_r4_wifi                           │
╰────────────────────────────────────────────────────╯

Firmware available for Arduino Uno R4 WiFi:
   1  serial_test  sketches/arduino/renesas_uno/unor4wifi/serial_test
   2  blink        sketches/arduino/renesas_uno/unor4wifi/blink
   3  PlatformIO heartbeat [uno_r4_wifi]  sketches/platformio/heartbeat
   4  Skip this board
   5  Quit FlashBot
Select: 1

serial_test -> Arduino Uno R4 WiFi (/dev/ttyACM0)
> Build
Build succeeded
> Upload
Upload succeeded
> Test
  Test      Result   Detail
  ping       PASS    PONG
  led_on     PASS    OK
  led_off    PASS    OK

Success  serial_test on Arduino Uno R4 WiFi, all tests passed (14.2s)
```

To flash a single board and exit, which is useful in scripts:

```bash
flashbot flash serial_test
```

---

## Workspace layout

FlashBot reads firmware from, and writes its state to, a workspace directory:

```
<workspace>/
├── sketches/    Arduino sketches and PlatformIO projects
├── config/      user_boards.json, firmware_manifest.json (generated)
├── build/       compiler output, one directory per board and sketch
└── logs/        flashbot.db
```

The workspace is resolved in this order: the `--workspace` option, the `FLASHBOT_HOME` environment variable, the current directory if it contains `sketches/`, and finally `~/.flashbot`. Create a new workspace with `flashbot init <path>`.

### Arduino sketches

The folder path encodes the board's FQBN:

```
sketches/<vendor>/<arch>/<board>[/<option>=<value>...]/<name>/<name>.ino
```

| FQBN | Sketch location |
|------|-----------------|
| `arduino:avr:uno` | `sketches/arduino/avr/uno/blink/blink.ino` |
| `arduino:avr:nano:cpu=atmega328old` | `sketches/arduino/avr/nano/cpu=atmega328old/imu/imu.ino` |
| `esp32:esp32:esp32s3` | `sketches/esp32/esp32/esp32s3/web_server/web_server.ino` |
| `rp2040:rp2040:rpipico` | `sketches/rp2040/rp2040/rpipico/blink/blink.ino` |

The `.ino` file name must match its folder name. Extra source files (`.cpp`, `.h`) in the sketch folder are compiled and included in change detection. Libraries the sketch depends on can be declared in `flashbot.json` (see [Libraries](#libraries)) so it builds on any machine.

### PlatformIO projects

Any directory under `sketches/` that contains a `platformio.ini` is treated as a PlatformIO project. Each `[env:...]` section becomes a separate target and is offered for boards whose PlatformIO board ID matches the environment's `board` value.

```ini
[env]
framework = arduino
monitor_speed = 115200

[env:esp32dev]
platform = espressif32
board = esp32dev
```

Library dependencies are declared with `lib_deps` in `platformio.ini`, as usual for PlatformIO.

For a board whose PlatformIO ID cannot be inferred from its FQBN, either register the board with `--pio-board`, or pin the environment to an FQBN:

```ini
[env:custom]
board = my_custom_board
custom_flashbot_fqbn = esp32:esp32:esp32s3
```

New sketches and projects are picked up while FlashBot is running; no restart is required.

---

## Command reference

| Command | Description |
|---------|-------------|
| `flashbot` or `flashbot run` | Watch for boards and run the pipeline interactively. |
| `flashbot run --auto` | Unattended mode: no prompts, newest matching firmware, unknown boards skipped. |
| `flashbot run --auto --jobs N` | Unattended mode, flashing up to N boards in parallel. |
| `flashbot flash [TARGET]` | Build, flash, and test one connected board, then exit with a status code. |
| `flashbot build [TARGET]` | Compile without hardware. Builds every target when none is given. |
| `flashbot sketches` | List discovered firmware targets. |
| `flashbot devices` | List connected serial devices and how they were identified. |
| `flashbot boards list` | List built-in and user-registered boards. |
| `flashbot boards add [VID:PID]` | Register a board. Defaults to the connected unrecognised board. |
| `flashbot boards remove VID:PID` | Remove a user registration. |
| `flashbot monitor [PORT]` | Open the serial monitor. |
| `flashbot plotter [PORT]` | Open the terminal serial plotter. |
| `flashbot report` | Show flash history and failure summary. |
| `flashbot init [PATH]` | Create a workspace. |
| `flashbot doctor` | Check toolchains, cores, permissions, and the workspace. |

`TARGET` is a sketch or project path, or the name of a discovered sketch. Common options:

| Option | Applies to | Description |
|--------|------------|-------------|
| `-w, --workspace DIR` | all | Use a specific workspace. |
| `-p, --port PORT` | `flash` | Serial port of the board. |
| `--fqbn FQBN` | `flash`, `build` | Override or filter by FQBN. Required to build a sketch outside `sketches/`. |
| `-e, --env NAME` | `flash`, `build` | PlatformIO environment. |
| `-y, --yes` | `flash` | Never prompt. |
| `--sketch NAME` | `run` | Only flash the named sketch or project. |
| `-j, --jobs N` | `run --auto` | Flash up to N boards in parallel. Default 1. |
| `--json FILE` | `flash`, `build` | Write results as JSON. |
| `--junit FILE` | `flash`, `build` | Write results as JUnit XML. |
| `--no-test` | `run`, `flash` | Skip post-flash tests. |
| `--no-cache` | `run`, `flash` | Recompile even if sources are unchanged. |
| `-b, --baud RATE` | `monitor`, `plotter` | Baud rate. Prompted if omitted. |
| `-l, --log FILE` | `monitor` | Also write output to a file. |
| `--labels NAME...` | `plotter` | Names for unlabelled CSV columns. |
| `-n, --limit N` / `--failed` | `report` | Number of rows / only failed runs. |

Exit codes: `0` success, `1` pipeline or build failure, `2` usage or configuration error, `130` interrupted.

---

## Sketch settings and tests

A `flashbot.json` file next to an Arduino sketch, or in the root of a PlatformIO project, holds per-sketch settings: library dependencies and the post-flash test suite. Every key is optional.

### Libraries

```json
{
  "libraries": ["Adafruit BMP280 Library", "Servo@1.2.1"]
}
```

Before compiling an Arduino sketch, FlashBot installs the listed libraries with `arduino-cli lib install`. Names are as shown by `arduino-cli lib search`; append `@version` to pin a release. Already-installed libraries are left as they are. PlatformIO projects use `lib_deps` instead.

### Post-flash tests

After uploading, FlashBot waits for the board to re-enumerate (the port path may change), opens the serial port, and runs the sketch's test suite. Without a test file the suite checks that the port opens, which confirms the new firmware booted.

To define tests, add them to `flashbot.json`:

```json
{
  "baud": 9600,
  "boot_delay": 2.0,
  "tests": [
    {"name": "boot_banner", "expect": "READY", "timeout": 5},
    {"name": "ping", "send": "PING", "expect": "PONG"},
    {"name": "status", "send": "STATUS", "expect": "^OK", "regex": true}
  ]
}
```

| Field | Description |
|-------|-------------|
| `baud` | Optional. Defaults to the PlatformIO `monitor_speed`, then the first `Serial.begin()` in the source, then 9600. |
| `boot_delay` | Seconds to wait after opening the port before testing. Default 2.0. |
| `tests[].send` | Line to send. Omit to only wait for output. |
| `tests[].expect` | Text that a received line must contain (or match, with `regex`). Omit to accept any reply. |
| `tests[].timeout` | Seconds to wait for a matching line. Default 2.0. |

Tests that only wait for output (no `send`) see what the board prints after FlashBot opens the port. Boards that reset when the port opens (Uno, Nano, Mega, and ESP32 boards with a CP210x or CH340 bridge) print their boot output again at that point. Boards with native USB (Uno R4, Leonardo, Pico, ESP32-C3/S3) do not, so a message printed only once at boot can be missed; for those, test periodic output or use a `send` and `expect` pair.

A run is recorded as successful only if the build, the upload, and every test pass.

---

## Board registration

When an unrecognised board is connected in interactive mode, FlashBot shows its USB ID and offers a list of common boards. The registration is stored in `config/user_boards.json`:

```json
{
  "1a86:7523": {
    "name": "Nano clone",
    "fqbn": "arduino:avr:nano:cpu=atmega328old"
  }
}
```

Registrations can also be managed directly:

```bash
flashbot boards add 1a86:7523 --name "Nano clone" --fqbn arduino:avr:nano:cpu=atmega328old
flashbot boards add 16c0:0483 --name "Teensy 4.1" --fqbn teensy:avr:teensy41
flashbot boards remove 1a86:7523
```

---

## Unattended operation

`flashbot run --auto` never prompts. For each recognised board it flashes the most recently modified matching firmware (or the one named with `--sketch`), runs the tests, records the result, and waits for the next board. Unknown boards are logged and skipped.

### Parallel flashing

With `--jobs N`, up to N boards are handled at the same time, which suits labs and production stations with a USB hub:

```bash
flashbot run --auto --jobs 4 --sketch serial_test
```

Each output line is prefixed with the board's port, for example `[ttyUSB0]`. Boards that share a build directory (the same sketch for the same FQBN) compile and upload one at a time, while their tests still run in parallel. Identical boards without a USB serial number, such as two CH340 clones, are told apart by their port.

### systemd

`flashbot.service` is a template unit for a dedicated flashing station. Edit the user and paths, then:

```bash
sudo cp flashbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flashbot
journalctl -u flashbot -f
```

### Docker

The image includes arduino-cli with the AVR, Renesas, ESP32, and RP2040 cores, and PlatformIO Core.

```bash
docker compose up --build
```

The container runs privileged with `/dev` and `/run/udev` mounted so it can see hotplug events. `sketches/`, `config/`, `logs/`, and `build/` are mounted from the host.

### Continuous integration

`flashbot build` compiles every target without hardware and exits non-zero on failure, so it can gate pull requests. `flashbot build` and `flashbot flash` can also write their results for CI dashboards: `--junit` produces JUnit XML with one test suite per target and one test case per step (build, upload, and each post-flash test), and `--json` produces a JSON summary.

```bash
flashbot build                                        # all targets
flashbot build --fqbn esp32:esp32:esp32 --junit reports/esp32.xml
flashbot build sketches/platformio/heartbeat --env esp32dev
flashbot flash serial_test --yes --json reports/flash.json
```

The repository's GitHub Actions workflow (`.github/workflows/ci.yml`) runs the unit tests on Python 3.10 to 3.13, compiles the Uno R4 and Nano firmware with arduino-cli and PlatformIO, and uploads the JUnit reports as build artifacts.

---

## Configuration

| Setting | Location | Purpose |
|---------|----------|---------|
| `FLASHBOT_HOME` | environment | Workspace directory. |
| `config/user_boards.json` | workspace | User board registrations (VID:PID to name, FQBN, optional PlatformIO board). |
| `config/firmware_manifest.json` | workspace | Generated list of discovered targets. Not intended for editing. |
| `flashbot.json` | sketch or project folder | Library dependencies, post-flash tests, and baud rate. |
| `custom_flashbot_fqbn` | `platformio.ini` environment | Pins a PlatformIO environment to an FQBN. |
| `logs/flashbot.db` | workspace | SQLite history of all runs. |

---

## Architecture

```
USB hotplug ──> detector ──> cli (Session) ──> pipeline ──> flasher ──> tester ──> logger
                   │                │                          │
              boards registry   firmware scanner         arduino-cli / pio
```

```
src/flashbot/
├── cli.py                 Argument parsing and command implementations
├── ui.py                  Rich panels, menus, and prompts
├── workspace.py           Workspace resolution
├── doctor.py              Environment checks
├── detector/
│   ├── boards.py          Built-in USB IDs, user registry, FQBN to PlatformIO mapping
│   ├── device_id.py       Port enumeration, identification, re-enumeration tracking
│   └── usb_listener.py    udev listener with polling fallback
├── firmware/
│   ├── targets.py         FirmwareTarget (Arduino sketch or PlatformIO environment)
│   ├── scanner.py         Discovery and manifest generation
│   ├── spec.py            flashbot.json reading
│   ├── platformio.py      platformio.ini parsing
│   └── watcher.py         Live rescan on filesystem changes
├── flasher/
│   ├── __init__.py        get_flasher(target) factory
│   ├── base.py            BaseFlasher, tool execution, source hashing, error hints
│   ├── arduino_cli.py     Generic arduino-cli flasher with build caching
│   ├── esp32.py           ESP32 upload retry
│   └── platformio.py      PlatformIO flasher
├── pipeline/
│   └── state_machine.py   Build, flash, test, record
├── tester/
│   ├── test_cases.py      flashbot.json loading and baud detection
│   ├── serial_comm.py     Line-oriented serial I/O
│   └── test_runner.py     Test execution
├── logger/
│   ├── result_store.py    SQLite storage and migrations
│   ├── export.py          JSON and JUnit XML results
│   └── reporter.py        History report
└── tools/
    ├── serial_base.py     Serial connection and port selection
    ├── serial_monitor.py  Serial monitor
    └── serial_plotter.py  Serial plotter
```

Design notes:

- **Hotplug events are processed on the main thread.** The listener thread only enqueues events, so prompts and Ctrl+C behave normally and events from a board resetting after upload are discarded by a short cooldown.
- **The flasher factory selects the toolchain.** Adding a toolchain means one new `BaseFlasher` subclass and one branch in `get_flasher`; the pipeline is unchanged.
- **Build caching is per sketch and per FQBN.** The cache key is a SHA-256 of every source file in the sketch folder, and each sketch has its own build directory, so a cached binary always belongs to the sketch being flashed.
- **The state machine is hardware-independent.** The flasher, port waiter, and test runner are injected, which is how the unit tests exercise every failure path.

---

## Troubleshooting

**No firmware found for a board.** The folder path does not produce the board's FQBN. Run `flashbot sketches` to see what was discovered and any path warnings, and `flashbot devices` to see the detected FQBN.

**Permission denied on `/dev/ttyACM0` or `/dev/ttyUSB0`.** Add your user to the `dialout` group and log in again: `sudo usermod -aG dialout $USER`.

**Device or resource busy.** Another program holds the port, often ModemManager on Ubuntu. Close other serial monitors, or run `sudo systemctl disable --now ModemManager`.

**Platform not installed.** Install the core named in the error, for example `arduino-cli core install esp32:esp32`. `flashbot doctor` lists installed cores.

**ESP32 upload fails to connect.** Hold the BOOT button while the upload starts. Boards without auto-reset circuitry may need a 10 uF capacitor between EN and GND.

**Board did not reappear after upload.** The board may need longer to boot, or it may have enumerated with a different USB ID (for example a Pico running MicroPython). Check with `flashbot devices`.

**Wrong board detected for a USB-serial bridge.** Register the correct board for that USB ID with `flashbot boards add VID:PID`.

---

## Development

```bash
poetry install
poetry run pytest
```

The test suite covers discovery, PlatformIO parsing, board registration, test-suite loading, the plotter parser, and every pipeline outcome, without requiring hardware. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

The documentation site lives in `docs/` and is plain HTML, CSS, and JavaScript suitable for GitHub Pages.

---

## Roadmap

| Version | Scope |
|---------|-------|
| 0.4.0 | OTA uploads for ESP32; validated macOS support |
| 0.5.0 | Web dashboard for flashing stations |
| 1.0.0 | Stable configuration format and plugin interface for custom flashers |

---

## License

FlashBot is released under the [MIT License](LICENSE).
