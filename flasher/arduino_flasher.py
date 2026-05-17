import subprocess
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
        run = subprocess.run(
            ["arduino-cli", "upload", "--port", port, "--fqbn", self.fqbn, sketch_path],
            capture_output=True,
            text=True
        )
        if run.returncode != 0:
            print(f"Flash failed:\n{run.stderr}")
            return False
        print("Flash successful.")
        return True

    def get_supported_fqbns(self) -> list[str]:
        return [
            "arduino:avr:uno",
            "arduino:avr:mega",
            "arduino:a"
        ]