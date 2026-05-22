import subprocess
import time
from flasher.base_flasher import BaseFlasher

class ArduinoFlasher(BaseFlasher):

    def __init__(self, fqbn: str):
        self.fqbn = fqbn

    def build(self, sketch_path: str) -> bool:
        run = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", self.fqbn, sketch_path],
            capture_output=True,
            text=True
        )
        if run.returncode != 0:
            print(f"Build failed:\n{run.stderr}")
            return False
        print("Build successful.")
        return True

    def flash(self, port: str, sketch_path: str) -> bool:
        for attempt in range(2):
            run = subprocess.run(
                ["arduino-cli", "upload", "--port", port, "--fqbn", self.fqbn, sketch_path],
                capture_output=True,
                text=True
            )
            if run.returncode == 0:
                print("Flash successful.")
                return True
            print(f"Flash attempt {attempt + 1} failed:\n{run.stderr}")
            time.sleep(1)
        return False

    def get_supported_fqbns(self) -> list[str]:
        return [
            "arduino:avr:uno",
            "arduino:avr:mega",
            "arduino:avr:nano",
            "arduino:avr:leonardo",
            "arduino:avr:micro",
            "arduino:renesas_uno:unor4wifi"
        ]