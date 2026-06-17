# FlashBot

**Version: v0.1.0-alpha**

> *Plug in your microcontroller. FlashBot detects, compiles, flashes, tests, and logs — automatically.*

---

## What is FlashBot?

FlashBot is a Python CLI tool that automates the entire embedded firmware workflow for Arduino boards (ESP32 support stubbed). 

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
- **Unknown board?** Shows raw USB IDs and asks for name + FQBN once. Remembers forever in `config/user_boards.json`.

### 3. Sketch Selection
Scans the `sketches/` folder tree to find all firmware projects for your specific board. Auto-selects if only one exists, otherwise shows a numbered menu.

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

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Linux** (tested on Ubuntu; uses `pyudev` for USB hotplug)
- **arduino-cli** in your PATH

```bash
# 1. Install Python dependencies
pip install pyserial pyudev rich

# 2. Install arduino-cli
# https://arduino.github.io/arduino-cli/latest/installation/

# 3. Install your Arduino core
arduino-cli core update-index
arduino-cli core install arduino:avr          # Uno, Nano, Mega
arduino-cli core install arduino:renesas_uno  # Uno WiFi R4

# 4. Clone and run
cd ~/Desktop/repos/FlashBot-old
python flashbot.py
```

---

## Usage

### Main pipeline

```bash
python flashbot.py
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

Flash another sketch? [y/n] (n):
```

### View history

```bash
python flashbot.py report
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
Enter FQBN [arduino:avr:uno]: esp32:esp32:esp32
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
├── flashbot.py              ← Rich CLI entry point (run this)
├── main.py                  ← Plain CLI fallback (no Rich)
│
├── config/
│   ├── firmware_manifest.json      ← Auto-generated from sketches/
│   ├── sketch_scanner.py           ← Walks sketches/ and updates manifest
│   └── user_boards.json            ← Your custom board registrations
│
├── detector/
│   ├── device_id.py                ← BOARD_TABLE + unknown board prompt
│   └── usb_listener.py             ← udev hotplug listener thread
│
├── flasher/
│   ├── __init__.py                 ← Factory: get_flasher(fqbn)
│   ├── base_flasher.py             ← Abstract contract
│   ├── arduino_flasher.py          ← arduino-cli compile + upload
│   └── esptool_flasher.py          ← 🚧 Stub — compile works, flash pending
│
├── logger/
│   ├── result_store.py             ← SQLite init, save, query
│   └── reporter.py                 ← Plain-text reporter CLI
│
├── sketches/
│   └── <vendor>/<arch>/<board>/<sketch>/<sketch>.ino
│       e.g. arduino/avr/uno/blink/blink.ino
│       e.g. esp32/esp32/esp32/blink/blink.ino
│
├── tester/
│   ├── serial_comm.py              ← pyserial wrapper with retry logic
│   ├── test_cases.py               ← Sketch-to-test mapping
│   └── test_runner.py              ← Executes tests over serial
│
├── tests/
│   └── test_pipeline.py            ← Unit tests (placeholder)
│
├── smoke_test.py                 ← Quick sanity check
└── README.md                       ← This file
```

### Why this structure matters

The **factory pattern** in `flasher/__init__.py` means `main.py` and `flashbot.py` never hardcode board names. Adding ESP32, STM32, or Teensy requires **one new file + one line** in the factory. The orchestration files never change.

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

Drop a new `.ino` into the correct path and restart FlashBot. The manifest updates automatically. No hand-editing JSON.

---

## Architecture

```
USB plug
    ↓
detector/          ← udev events → DetectedDevice or UnknownBoard
    ↓
flashbot.py        ← Rich UI, prompts, orchestration
    ↓
flasher/           ← Factory picks ArduinoFlasher or ESPToolFlasher
    ↓
tester/            ← SerialComm + TestRunner validates firmware
    ↓
logger/            ← SQLite persistence + reporter CLI
    ↓
config/            ← Auto-generated manifest + user board registry
```

### Key design decisions

| Decision | Why |
|----------|-----|
| **Factory pattern** | Adding a board family = 1 file + 1 line. No changes to main orchestration. |
| **Hash-guarded builds** | SHA-256 of `.ino` stored in DB. Skips compile if unchanged since last success. |
| **Unknown board flow** | Prompts for name + FQBN, persists to JSON. Survives restarts. |
| **Sketch folder tree** | `sketches/<vendor>/<arch>/<board>/` auto-maps to FQBN. Manifest regenerates on startup. |
| **Rich CLI** | Colored panels, tables, spinners, and styled prompts in `flashbot.py`. Plain `main.py` still works as fallback. |

---

## Current Status

| Feature | Status | Notes |
|---------|--------|-------|
| USB hotplug detection | ✅ Ready | Linux `pyudev` |
| Arduino compile + flash | ✅ Ready | `arduino-cli` with `--input-dir` for build cache |
| Incremental builds (hash guard) | ✅ Ready | SHA-256 check against SQLite |
| Post-flash serial testing | ✅ Ready | Per-sketch test suites |
| SQLite logging + history reporter | ✅ Ready | `flashbot.py report` |
| Unknown board registration | ✅ Ready | Persists to `config/user_boards.json` |
| Auto-generated sketch manifest | ✅ Ready | Scans `sketches/` on startup |
| Rich CLI (colors, tables, spinners) | ✅ Ready | `flashbot.py` |
| ESP32 flashing | ✅ Ready| Compiles via `arduino-cli`, upload pending real `esptool.py` |
| STM32 / Teensy / Pico | ⬜ Planned | Architecture ready, needs flasher classes |
| Non-interactive / CI mode | ⬜ Planned | For lab automation |

---

## Troubleshooting

### "No sketches configured for [board name]"

Your `sketches/` folder doesn't have a path matching that FQBN. Check `config/firmware_manifest.json` to see what was detected.

### "Compiled sketch not found in ..."

The build cache path and upload path got out of sync. Fixed in current `arduino_flasher.py` by passing `--input-dir` to upload. If you see this, make sure your `flasher/arduino_flasher.py` has the `self.build_dir` logic.

### "No flasher registered for FQBN"

The board is recognized but there's no flasher class for its family. Currently only `arduino:` FQBNs have full flashers. ESP32 is stubbed.

### Board prompts again after flash

Arduino boards reset after upload and briefly re-enumerate on USB. FlashBot has a 5-second debounce cooldown. Wait a moment after flashing before answering prompts.

### "ImportError: cannot import name 'ResultStore'"

You have an old `result_store.py` from a different branch. The current codebase uses plain functions (`save_result`, `get_results`). Make sure `reporter.py` matches.

---

## Roadmap

- **v0.2.0** — Full ESP32 support via `esptool.py`
- **v0.3.0** — Non-interactive mode for batch flashing in labs
- **v0.4.0** — STM32, Teensy, Raspberry Pi Pico support
- **v1.0.0** — Stable multi-platform release with documentation site

---

## Files to Commit

When you're ready to push to GitHub, commit these:

```
# Core pipeline
flashbot.py
main.py

# Detection
detector/__init__.py
detector/device_id.py
detector/usb_listener.py

# Flashing abstraction
flasher/__init__.py
flasher/base_flasher.py
flasher/arduino_flasher.py
flasher/esptool_flasher.py

# Testing
tester/__init__.py
tester/serial_comm.py
tester/test_cases.py
tester/test_runner.py

# Logging
logger/__init__.py
logger/result_store.py
logger/reporter.py

# Configuration + manifest
config/__init__.py
config/sketch_scanner.py
config/firmware_manifest.json    # auto-generated, but useful as reference

# Sketches (your firmware projects)
sketches/

# Tests
smoke_test.py
tests/test_pipeline.py

# Documentation
README.md

# Not committed (add to .gitignore):
# logs/           ← SQLite DB + build artifacts
# build/          ← arduino-cli compile cache
# venv/           ← Python virtual environment
# __pycache__/    ← Python bytecode
# config/user_boards.json   ← personal board registrations
```

---

## License

MIT

---

