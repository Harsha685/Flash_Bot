# FlashBot

An automated firmware flashing and testing pipeline for Arduino boards.
Plug in a board — FlashBot detects it, compiles the firmware, flashes it, and logs the result. No IDE, no manual steps.

---

## What it does

- Detects boards the moment they are plugged in via Linux udev events
- Looks up the right firmware from a config file based on board VID/PID
- Compiles and flashes using arduino-cli
- Logs every flash result to a SQLite database
- Supports Arduino UNO R4 WiFi, Nano (FTDI, CH340), Uno, Mega, Leonardo, Micro

---

## Project structure
FlashBot/
├── main.py                        # entry point
├── detector/
│   ├── device_id.py               # board detection via VID/PID lookup
│   └── usb_listener.py            # watches /dev/ for new boards
├── flasher/
│   ├── base_flasher.py            # abstract base class
│   └── arduino_flasher.py         # arduino-cli compile + upload
├── tester/
│   └── serial_comm.py             # serial communication with board
├── logger/
│   └── result_store.py            # SQLite logging
├── config/
│   └── firmware_manifest.json     # maps board FQBN to sketches
├── sketches/
│   ├── blink/blink.ino            # LED blink + serial command listener
│   └── serial_test/serial_test.ino
└── requirements.txt

---

## Requirements

- Linux (tested on Ubuntu 24)
- Python 3.10+
- arduino-cli
- avrdude

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/FlashBot.git
cd FlashBot
```

**2. Create a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**4. Install arduino-cli**
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
```

**5. Install board cores**
```bash
arduino-cli core update-index
arduino-cli core install arduino:renesas_uno
arduino-cli core install arduino:avr
```

**6. Set up USB permissions**
```bash
sudo "/home/$USER/.arduino15/packages/arduino/hardware/renesas_uno/1.5.3/post_install.sh"
sudo usermod -a -G dialout $USER
```
Log out and back in after running the usermod command.

---

## Usage

**Run the pipeline**
```bash
python main.py
```
Plug in your board. FlashBot will detect it, show available sketches, flash the selected one, and exit.

**Register a new board/sketch**
```bash
python main.py register
```
Detects the connected board and lets you assign a sketch to it. Saves to `firmware_manifest.json`.

---

## Adding a new board

**Step 1** — find the VID/PID:
```bash
arduino-cli board list --json
```

**Step 2** — add to `BOARD_TABLE` in `detector/device_id.py`:
```python
("vid", "pid"): {"name": "Board Name", "fqbn": "platform:arch:board"},
```

**Step 3** — add to `config/firmware_manifest.json`:
```json
"platform:arch:board": {
    "sketches": ["sketches/your_sketch/your_sketch.ino"]
}
```

Or just run `python main.py register` and it does steps 1 and 3 automatically.

---

## How it works
Board plugged in
│
▼
usb_listener.py detects ttyACM* or ttyUSB* in /dev/
│
▼
device_id.py matches VID/PID to board name + FQBN
│
▼
firmware_manifest.json looked up for sketches
│
▼
arduino_flasher.py compiles + uploads via arduino-cli
│
▼
result_store.py logs result to flashbot.db
│
▼
Exit

---

## Supported boards

| Board | VID | PID | FQBN |
|---|---|---|---|
| Arduino UNO R4 WiFi | 2341 | 1002 | arduino:renesas_uno:unor4wifi |
| Arduino Uno | 2341 | 0043 | arduino:avr:uno |
| Arduino Nano (FTDI) | 0403 | 6001 | arduino:avr:nano |
| Arduino Nano (CH340) | 1a86 | 7523 | arduino:avr:nano |
| Arduino Mega | 2341 | 0010 | arduino:avr:mega |
| Arduino Leonardo | 2341 | 8036 | arduino:avr:leonardo |
| Arduino Micro | 2341 | 8037 | arduino:avr:micro |

---

## Database

Every flash run is logged to `flashbot.db`. You can query it directly:

```bash
sqlite3 flashbot.db "SELECT * FROM flash_runs ORDER BY timestamp DESC LIMIT 10;"
```

---

## Roadmap

- [ ] ESP32 support via esptool
- [ ] STM32 support via st-flash
- [ ] CLI with rich terminal UI
- [ ] Docker support
- [ ] pytest suite with mocked hardware

---

## License

MIT
