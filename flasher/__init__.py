from flasher.arduino_flasher import ArduinoFlasher

def get_flasher(fqbn: str):
    if fqbn.startswith("arduino:"):
        return ArduinoFlasher(fqbn)
    
    raise ValueError(f"No flasher registered for FQBN: {fqbn}")