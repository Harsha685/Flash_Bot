from flashbot.flasher.arduino_flasher import ArduinoFlasher
from flashbot.flasher.esptool_flasher import EspFlasher

def get_flasher(fqbn: str):
    if fqbn.startswith("arduino:"):
        return ArduinoFlasher(fqbn)
    if fqbn.startswith("esp32:"):
        return EspFlasher(fqbn)
    
    raise ValueError(f"No flasher registered for FQBN: {fqbn}")