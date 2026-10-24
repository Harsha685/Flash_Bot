# Contributing to FlashBot

Contributions are welcome, particularly from developers with access to boards that the maintainers cannot test. This document describes how to set up a development environment and the most common kinds of contribution.

## Development setup

```bash
git clone https://github.com/Harsha685/Flash_Bot.git
cd Flash_Bot
poetry install
poetry run pytest
poetry run flashbot doctor
```

Without Poetry, use a virtual environment and `pip install -e .` followed by `pip install pytest`.

## Adding a board to the built-in table

Boards that can be identified unambiguously from their USB ID belong in `BUILTIN_BOARDS` in `src/flashbot/detector/boards.py`:

```python
("2341", "0043"): BoardInfo("Arduino Uno", "arduino:avr:uno"),
```

- Find the VID and PID with `lsusb` (for example `ID 2341:0043`). Use lowercase hexadecimal without a `0x` prefix.
- Find the FQBN with `arduino-cli board listall`.
- If the board has a PlatformIO equivalent, add the FQBN to `FQBN_TO_PIO` in the same file. The PlatformIO ID is listed by `pio boards`.
- Do not add generic USB-serial bridges or debug probes that are shared by many boards (for example the Teensy serial ID or ST-LINK). Add those boards to `COMMON_BOARDS` instead so users can select them during registration.

## Adding a toolchain

Arduino-compatible cores and PlatformIO platforms are already supported through `ArduinoCliFlasher` and `PlatformIOFlasher`. A new flasher is only needed for a different build or upload tool.

1. Create `src/flashbot/flasher/<name>.py` with a subclass of `BaseFlasher`:

   ```python
   from flashbot.flasher.base import BaseFlasher, StepResult, run_tool


   class ExampleFlasher(BaseFlasher):
       def build(self) -> StepResult:
           proc = run_tool(["example-tool", "build", str(self.source_dir)], "Building")
           if proc.returncode != 0:
               return StepResult(ok=False, error=self._failure("Build", proc))
           return StepResult(ok=True)

       def flash(self, port: str) -> StepResult:
           proc = run_tool(["example-tool", "upload", "--port", port, str(self.source_dir)], "Uploading")
           if proc.returncode != 0:
               return StepResult(ok=False, error=self._failure("Upload", proc))
           return StepResult(ok=True)
   ```

2. Select it in `get_flasher` in `src/flashbot/flasher/__init__.py`.
3. Add tests. The pipeline tests in `tests/test_pipeline.py` show how to inject a fake flasher.

## Adding tests for a sketch

Serial tests and library dependencies are declared in a `flashbot.json` file next to the sketch rather than in code. If you add a sketch that uses a library, list it under `libraries` so the sketch builds in CI. See the "Sketch settings and tests" section of the README for the format, and `sketches/arduino/renesas_uno/unor4wifi/serial_test/` for an example.

## Coding guidelines

- Target Python 3.10 and use type hints on public functions.
- Keep the pipeline hardware-independent: anything that touches a tool or a port should be injectable.
- Print through the shared console in `flashbot.console`. Print device output as `rich.text.Text`, never as markup.
- Avoid new runtime dependencies unless they are clearly necessary.
- Add or update tests for behaviour changes, and update the README and `docs/` when commands or formats change.

## Submitting changes

1. Fork the repository and create a descriptively named branch, for example `add-nano-esp32`.
2. Make your changes and run `poetry run pytest`.
3. Test with real hardware where possible, and state in the pull request which boards you used.
4. Open a pull request that describes the change and its motivation.

## Reporting issues

Open an issue at https://github.com/Harsha685/Flash_Bot/issues and include:

- The output of `flashbot doctor` and `flashbot devices`
- The board, its FQBN or PlatformIO environment, and your operating system
- The command you ran and the complete output
