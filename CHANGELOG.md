# Changelog

All notable changes to this project are documented in this file.

## 0.3.0

### Added

- PlatformIO support. Projects with a `platformio.ini` anywhere under `sketches/` are discovered automatically, and each environment is matched to connected boards by PlatformIO board ID or by an explicit `custom_flashbot_fqbn`.
- Generic arduino-cli flasher, which enables Raspberry Pi Pico (RP2040), Teensy, STM32, SAMD, megaAVR, and any other installed core.
- Automatic identification of additional boards: Uno R4 Minima, Nano Every, Nano 33 IoT, Mega 2560 R3, Raspberry Pi Pico and Pico W, ESP32-S2 native USB.
- Board registration list grouped by vendor, including Teensy and STM32 Nucleo boards.
- Unattended mode (`flashbot run --auto`) for flashing stations and systemd.
- `flashbot flash` for single-board runs with meaningful exit codes.
- `flashbot build` for compiling without hardware, suitable for CI.
- `flashbot devices`, `flashbot sketches`, `flashbot boards`, `flashbot init`, and `flashbot doctor`.
- Per-sketch test suites in `flashbot.json`, including wait-for-output tests and regular expressions.
- Library dependencies in `flashbot.json`, installed with arduino-cli before compiling. The bundled sketches that need libraries now declare them.
- Parallel flashing in unattended mode (`flashbot run --auto --jobs N`), with per-board output prefixes and per-build-directory locking.
- JSON and JUnit XML results for `flashbot build` and `flashbot flash` (`--json`, `--junit`).
- GitHub Actions workflow running the unit tests and firmware builds.
- Automatic baud rate detection from `Serial.begin()` or PlatformIO `monitor_speed`.
- Workspaces: FlashBot can be run from any directory using `FLASHBOT_HOME` or `~/.flashbot`.
- Unit test suite covering discovery, configuration, and every pipeline outcome.
- `--version` option and `python -m flashbot` entry point.

### Fixed

- Build failures were not detected and the pipeline continued to the upload stage.
- The unchanged-source build cache never took effect because the source hash was not recorded. It could also upload a binary from a different sketch built for the same board.
- Sketches in folders with FQBN options (for example `cpu=atmega328old`) were not discovered.
- A board resetting after upload could trigger a second pipeline run.
- Built-in boards were written into `user_boards.json` when a board was registered.
- Configuration and database paths depended on the current directory, and the Docker volume pointed at an unused copy of the configuration.
- Failed post-flash tests did not mark the run as failed. The test baud rate was fixed at 9600.
- Serial output containing square brackets could crash the serial monitor.
- History timestamps were stored in UTC but compared with local time.
- The systemd unit referred to a script that no longer exists, and the Docker image installed dependencies before copying the package.

### Changed

- Hotplug events are handled on the main thread, so prompts and Ctrl+C work reliably.
- Post-flash tests wait for the board to re-enumerate and follow it to a new port if the path changes.
- The flash history report shows the test outcome and failing stage.
- The generated `firmware_manifest.json` is no longer tracked in version control.
- The documentation site moved to `docs/` and was redesigned.

## 0.2.0

- Poetry packaging with the `flashbot` command.
- Live sketch watcher, board picker, baud rate picker, serial monitor, and serial plotter.
- Docker image with USB passthrough.

## 0.1.0

- Initial release: USB detection, arduino-cli build and upload, serial tests, and SQLite logging.
