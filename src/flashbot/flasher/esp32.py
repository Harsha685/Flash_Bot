from flashbot.flasher.arduino_cli import ArduinoCliFlasher


class Esp32Flasher(ArduinoCliFlasher):
    """ESP32 family via arduino-cli (esptool under the hood), with an upload retry
    because auto-reset into the bootloader occasionally misses on the first try."""

    upload_attempts = 2
    upload_hint = ("If the board does not enter the bootloader, hold BOOT while the upload "
                   "starts, or add a 10 uF capacitor between EN and GND.")
