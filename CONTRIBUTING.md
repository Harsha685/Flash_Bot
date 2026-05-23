# Contributing to FlashBot

Thanks for your interest in contributing. FlashBot is a small open source project and contributions are welcome — especially from embedded developers who work with boards I don't have access to.

---

## Ways to Contribute

### Add a new board

The board lookup table lives in `detector/device_id.py`. Adding a board is one dict entry:

```python
("vid", "pid"): {"name": "Your Board Name", "fqbn": "vendor:arch:board"},
```

To find the VID and PID of your board on Linux:

```bash
lsusb
```

The output looks like `ID 2341:0043` — `2341` is the VID, `0043` is the PID. Use lowercase without `0x` prefix.

To find the FQBN:

```bash
arduino-cli board listall
```

### Add a new flasher

If your board uses a different toolchain than `arduino-cli` (STM32, Teensy, RP2040), add a new flasher:

1. Create `flasher/your_flasher.py`
2. Inherit from `BaseFlasher`
3. Implement three methods:

```python
from flasher.base_flasher import BaseFlasher

class YourFlasher(BaseFlasher):

    def __init__(self, fqbn: str):
        self.fqbn = fqbn

    def build(self, sketch_path: str) -> bool:
        # compile the sketch, return True on success
        pass

    def flash(self, port: str, sketch_path: str) -> bool:
        # flash to board, return True on success
        pass

    def get_supported_fqbns(self) -> list[str]:
        return ["your:board:fqbn"]
```

4. Register it in `flasher/__init__.py`:

```python
from flasher.your_flasher import YourFlasher

def get_flasher(fqbn: str):
    if fqbn.startswith("your:"):
        return YourFlasher(fqbn)
    ...
```

That's it. The rest of the pipeline picks it up automatically.

### Add serial tests for a sketch

Open `tester/test_cases.py` and add a condition for your sketch name:

```python
elif "your_sketch" in sketch_name:
    return [
        TestCase("test_name", "COMMAND", "EXPECTED_RESPONSE", timeout=2),
    ]
```

Your sketch needs to respond over serial. Minimal example:

```cpp
void setup() { Serial.begin(9600); }

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "PING") Serial.println("PONG");
    }
}
```

### Report a bug

Open an issue at https://github.com/Harsha685/Flash_Bot/issues

Include:
- Your board name and FQBN
- Your Linux distro and version
- What you ran and what happened
- Any error output

---

## Getting Started

```bash
git clone https://github.com/Harsha685/Flash_Bot.git
cd Flash_Bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Submitting a Pull Request

1. Fork the repository on GitHub
2. Create a branch with a descriptive name:
   ```bash
   git checkout -b add-stm32-support
   ```
3. Make your changes
4. Test with a real board if possible
5. Commit with a clear message:
   ```bash
   git commit -m "add STM32F4 support via OpenOCD"
   ```
6. Push and open a pull request

---

## Code Style

- Python 3.10+
- Type hints on function signatures
- Keep new flashers consistent with `ArduinoFlasher` as a reference
- No external dependencies unless absolutely necessary — check `requirements.txt` before adding

---

## Questions

Open an issue or start a discussion on GitHub. Happy to help.
