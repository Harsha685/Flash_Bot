# FlashBot

**Version: v0.1.0-alpha**

> *Plug in your microcontroller. FlashBot detects, compiles, flashes, tests, and logs — automatically.*

---

## What is FlashBot?

FlashBot is a Python CLI tool that automates the entire embedded firmware workflow for Arduino and ESP32 boards.

If you develop hardware, you know the repetitive cycle:

1. Plug in your board
2. Open the Arduino IDE
3. Select the right board and port
4. Hit **Compile**
5. Hit **Upload**
6. Open the Serial Monitor
7. Type test commands to verify it works
8. Repeat

**FlashBot collapses steps 2–7 into one action:** plug in the board, pick your sketch (or let it auto-select), and watch the pipeline run.

---

## Who is this for?

- **Hobbyists** iterating on firmware who are tired of IDE clickfests
- **Students and labs** flashing multiple boards in batches
- **Embedded developers** who want a repeatable, logged pipeline

You should be comfortable with basic command-line usage and have `arduino-cli` installed.

---

## What FlashBot does, step by step

### 1. Detection
Listens for USB hotplug events at the OS level. Sees your board appear on `/dev/ttyACM0` or `/dev/ttyUSB0` and reads its hardware ID.

### 2. Identification
Checks the internal board database:
- **Known board?** Loads name and FQBN automatically.
- **Unknown board?** Shows raw USB IDs and lets you pick from a list of common boards (no need to know what an FQBN is). Remembers forever in `config/user_boards.json`.

### 3. Sketch Selection
Scans the `sketches/` folder tree to find all firmware projects for your specific board. Auto-selects if only one exists, otherwise shows a numbered menu. New sketches dropped in while FlashBot is running are picked up automatically — no restart needed.

### 4. Compilation
Calls `arduino-cli` to compile your sketch. If you already flashed this exact sketch successfully before, FlashBot computes a SHA-256 hash of the source file and **skips compilation entirely**.

### 5. Flashing
Uploads the compiled binary to your board over USB/serial.

### 6. Testing
After the board reboots, opens a serial connection and runs a test suite defined for that sketch:
- `blink` → verifies the serial port opens (proof the board booted)
- `echo`/`serial_test` → sends `HELLO`, expects `HELLO` back

### 7. Logging
Every result — success or failure — is saved to a local SQLite database (`logs/flashbot.db`). View history anytime with the built-in reporter.

### 8. Live Monitoring & Plotting
After a successful flash, you're prompted to open a live serial monitor or real-time plotter — pick a baud rate from a list, no need to remember the right number.

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Linux** (tested on Ubuntu; uses `pyudev` for USB hotplug)
- **arduino-cli** in your PATH
- **Poetry** ([install instructions](https://python-poetry.org/docs/#installation))

```bash
# 1. Install arduino-cli
# https://arduino.github.io/arduino-cli/latest/installation/

# 2. Install your Arduino core
arduino-cli core update-index
arduino-cli core install arduino:avr          # Uno, Nano, Mega
arduino-cli core install arduino:renesas_uno  # Uno WiFi R4
arduino-cli core install esp32:esp32          # ESP32 boards

# 3. Clone and install
git clone https://github.com/<your-username>/FlashBot.git
cd FlashBot
poetry install

# 4. Run
poetry run flashbot
```

Or activate the virtual environment so you can drop the `poetry run` prefix:
```bash
poetry shell
flashbot
```

---

## Usage

### Main pipeline

```bash
poetry run flashbot
```

Plug in a board. FlashBot handles the rest.

```
╭────────────────────────── Board Detected ──────────────────────────╮
│ Arduino Uno WiFi R4                                                │
│ Port:  /dev/ttyACM0                                                │
│ FQBN:  arduino:renesas_uno:unor4wifi                               │
╰────────────────────────────────────────────────────────────────────╯
Auto-selected: sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino
[dim]Sketch unchanged — skipping compile.[/dim]
[bold green]FLASH OK[/bold green]
[dim]Logged to database[/dim]
[bold green]All Tests Passed[/bold green]
  [green]✓ board_boots[/green]

What would you like to do?
  1. Open Serial Monitor
  2. Open Serial Plotter
  3. Skip
Select (3):
```

### Serial Monitor

```bash
poetry run flashbot monitor
```

Auto-detects the port, prompts you to pick a baud rate from a list. To specify manually:
```bash
poetry run flashbot monitor /dev/ttyUSB0 -b 115200
```

Log output to a file:
```bash
poetry run flashbot monitor -l logs/session1.log
```

### Serial Plotter

```bash
poetry run flashbot plotter
```

Expects numeric serial output in `key: value` or comma-separated format. Label CSV columns:
```bash
poetry run flashbot plotter --labels Temp Humidity Pressure
```

### View history

```bash
poetry run flashbot report
```

Output:
```
┌──────────────────────────────────── Flash History ────────────────────────────────────┐
│ ID  Board              FQBN                         Sketch              Status  Timestamp│
├───────────────────────────────────────────────────────────────────────────────────────┤
│ 3   Arduino Uno WiFi  arduino:renesas_uno:unor4wifi sketches/.../blink  SUCCESS 2026-... │
│ 2   Arduino Uno WiFi  arduino:renesas_uno:unor4wifi sketches/.../test SUCCESS 2026-... │
│ 1   Arduino Uno WiFi  arduino:renesas_uno:unor4wifi sketches/.../blink  FAILED  2026-... │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### Registering a new board

If FlashBot doesn't recognize your board:

```
╭────────────────────────── Unknown Board ───────────────────────────╮
│ Port:   /dev/ttyUSB0                                               │
│ VID:    10c4                                                       │
│ PID:    ea60                                                       │
│ Serial: 0001                                                       │
╰────────────────────────────────────────────────────────────────────╯
Register this board? [y/n] (y): y
Enter board name [My Board]: ESP32 DevKit

Select board type:
  1. Arduino Uno
  2. Arduino Nano (new bootloader)
  3. Arduino Nano (old bootloader)
  4. Arduino Mega 2560
  5. Arduino Leonardo
  6. Arduino Uno WiFi Rev4
  7. ESP32 Dev Module
  8. ESP32-S2
  9. ESP32-S3
  10. ESP32-C3
  11. Other (enter FQBN manually)
Select: 7
╭──────────────────────────── New Board ─────────────────────────────╮
│ Registered ESP32 DevKit                                            │
│ FQBN: esp32:esp32:esp32                                            │
╰────────────────────────────────────────────────────────────────────╯
```

Your answer is saved to `config/user_boards.json`. Next time, it's recognized instantly.

### Removing a registration

```bash
rm config/user_boards.json
```

The next plug will prompt you again.

---

## Project Structure

```
FlashBot/
├── pyproject.toml             ← Poetry config + entry point
├── poetry.lock
├── src/
│   └── flashbot/
│       ├── __init__.py
│       ├── cli.py             ← Rich CLI entry point
│       │
│       ├── config/
│       │   ├── firmware_manifest.json   ← Auto-generated from sketches/
│       │   ├── sketch_scanner.py        ← Walks sketches/ and updates manifest
│       │   ├── sketch_watcher.py        ← Live filesystem watcher (watchdog)
│       │   └── user_boards.json         ← Your custom board registrations
│       │
│       ├── detector/
│       │   ├── device_id.py             ← BOARD_TABLE, COMMON_BOARDS, unknown board flow
│       │   └── usb_listener.py          ← udev hotplug listener thread
│       │
│       ├── flasher/
│       │   ├── __init__.py              ← Factory: get_flasher(fqbn)
│       │   ├── base_flasher.py          ← Abstract contract
│       │   ├── arduino_flasher.py       ← arduino-cli compile + upload
│       │   └── esptool_flasher.py       ← ESP32 flashing via esptool
│       │
│       ├── logger/
│       │   ├── result_store.py          ← SQLite init, save, query
│       │   └── reporter.py              ← History reporter CLI
│       │
│       ├── pipeline/
│       │   └── state_machine.py         ← Orchestrates build → flash → test
│       │
│       ├── tester/
│       │   ├── serial_comm.py           ← pyserial wrapper with retry logic
│       │   ├── test_cases.py            ← Sketch-to-test mapping
│       │   └── test_runner.py           ← Executes tests over serial
│       │
│       └── tools/
│           ├── serial_base.py           ← Shared SerialConnection + port guessing
│           ├── serial_monitor.py        ← Live serial monitor
│           └── serial_plotter.py        ← Real-time ASCII/Rich plotter
│
├── sketches/
│   └── <vendor>/<arch>/<board>/<sketch>/<sketch>.ino
│       e.g. arduino/avr/uno/blink/blink.ino
│       e.g. esp32/esp32/esp32/blink/blink.ino
│
├── tests/
│   └── test_pipeline.py       ← Unit tests (placeholder)
│
└── README.md                  ← This file
```

### Why this structure matters

The **factory pattern** in `flasher/__init__.py` means `cli.py` never hardcodes board names. Adding STM32 or Teensy requires **one new file + one line** in the factory. The orchestration files never change.

The **Poetry packaging** means FlashBot installs and runs like a real CLI tool (`flashbot`, `flashbot monitor`, `flashbot report`) instead of `python flashbot.py` from inside the project folder.

---

## Adding Your Own Sketches

FlashBot expects this folder structure, which maps directly to FQBNs:

```
sketches/<vendor>/<arch>/<board>/<sketch_name>/<sketch_name>.ino
```

| FQBN | Folder path |
|------|-------------|
| `arduino:avr:uno` | `sketches/arduino/avr/uno/blink/blink.ino` |
| `arduino:renesas_uno:unor4wifi` | `sketches/arduino/renesas_uno/unor4wifi/serial_test/serial_test.ino` |
| `esp32:esp32:esp32` | `sketches/esp32/esp32/esp32/blink/blink.ino` |
| `arduino:avr:nano:cpu=atmega328old` | `sketches/arduino/avr/nano/cpu=atmega328old/my_sketch/my_sketch.ino` |

Drop a new `.ino` into the correct path while FlashBot is running — the manifest updates automatically within a second thanks to the filesystem watcher. No restart, no hand-editing JSON.

**Folder name and filename must match exactly** (e.g. `mpu6050_test/mpu6050_test.ino`), or the scanner won't pick it up.

---

## Architecture

```
USB plug
    ↓
detector/          ← udev events → DetectedDevice or UnknownBoard
    ↓
cli.py             ← Rich UI, prompts, orchestration
    ↓
flasher/           ← Factory picks ArduinoFlasher or EspFlasher
    ↓
tester/            ← SerialComm + TestRunner validates firmware
    ↓
tools/             ← Optional live monitor / plotter after flash
    ↓
logger/            ← SQLite persistence + reporter CLI
    ↓
config/            ← Auto-updating manifest + user board registry
```

### Key design decisions

| Decision | Why |
|----------|-----|
| **Factory pattern** | Adding a board family = 1 file + 1 line. No changes to main orchestration. |
| **Hash-guarded builds** | SHA-256 of `.ino` stored in DB. Skips compile if unchanged since last success. |
| **Live manifest watcher** | `watchdog` monitors `sketches/` in a background thread. No restart needed to see new sketches. |
| **Board picker over raw FQBN** | New users select from named boards instead of memorizing FQBN syntax. Manual entry remains as fallback. |
| **Poetry packaging** | `pyproject.toml` + `[tool.poetry.scripts]` gives a real `flashbot` command, mirroring tools like PlatformIO. |
| **Rich CLI** | Colored panels, tables, spinners, and styled prompts throughout. |

---

## Current Status

| Feature | Status | Notes |
|---------|--------|-------|
| USB hotplug detection | ✅ Ready | Linux `pyudev` |
| Arduino compile + flash | ✅ Ready | `arduino-cli` with `--input-dir` for build cache |
| ESP32 compile + flash | ✅ Ready | Via `esptool` |
| Incremental builds (hash guard) | ✅ Ready | SHA-256 check against SQLite |
| Live manifest auto-update | ✅ Ready | `watchdog`-based filesystem watcher |
| Board picker (no raw FQBN) | ✅ Ready | Falls back to manual entry if needed |
| Post-flash serial testing | ✅ Ready | Per-sketch test suites |
| Serial monitor + plotter | ✅ Ready | With interactive baud rate picker |
| SQLite logging + history reporter | ✅ Ready | `flashbot report` |
| Poetry packaging | ✅ Ready | `flashbot` installable CLI command |
| STM32 / Teensy / Pico | ⬜ Planned | Architecture ready, needs flasher classes |
| Non-interactive / CI mode | ⬜ Planned | For lab automation |
| `~/.flashbot/` user data dir | ⬜ Planned | Move sketches/DB out of package source |

---

## Troubleshooting

### "No sketches configured for [board name]"

Your `sketches/` folder doesn't have a path matching that FQBN. Check `src/flashbot/config/firmware_manifest.json` to see what was detected.

### Serial port busy / "Device or resource busy"

Another process (often ModemManager on Ubuntu) is holding the port. Free it:
```bash
sudo fuser -k /dev/ttyUSB0
sudo systemctl stop ModemManager
```
To stop this permanently:
```bash
sudo systemctl disable ModemManager
```

### ESP32 stuck resetting / "chip stopped responding"

Usually caused by the port being held open elsewhere, or the board not entering bootloader mode. Try the `fuser`/ModemManager fix above first, and hold the **BOOT** button if it persists.

### Folder/filename mismatch

If a new sketch isn't appearing, confirm the `.ino` filename matches its parent folder name exactly:
```bash
find sketches/ -name "*.ino"
```

### "ImportError: cannot import name 'X' from 'flashbot...'"

Usually a stale import path left over from before the Poetry restructure. All internal imports should be `from flashbot.<module>...`, not bare `from <module>...`.

---

## Roadmap

- **v0.2.0** — `~/.flashbot/` user data directory (sketches + DB outside package source)
- **v0.3.0** — Non-interactive mode for batch flashing in labs
- **v0.4.0** — STM32, Teensy, Raspberry Pi Pico support
- **v1.0.0** — Stable multi-platform release with documentation site

---

## License

MIT

---

