import os
import subprocess
from rich.console import Console
from rich.status import Status
from flasher.base_flasher import BaseFlasher
from logger.result_store import get_last_successful_hash

console = Console()

def _file_hash(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class ArduinoFlasher(BaseFlasher):
    def __init__(self, fqbn: str):
        self.fqbn = fqbn
        self.build_dir = f"build/{fqbn.replace(':', '_')}"

    def build(self, sketch_path: str, board_name: str = "") -> tuple[bool, str]:
        current_hash = _file_hash(sketch_path)
        last_hash = get_last_successful_hash(board_name, sketch_path)
        
        if current_hash == last_hash:
            console.print("[dim]Sketch unchanged — skipping compile.[/dim]")
            return True, current_hash
        
        os.makedirs(self.build_dir, exist_ok=True)
        
        with Status("[bold yellow]Compiling...", console=console) as status:
            run = subprocess.run(
                ["arduino-cli", "compile", "--fqbn", self.fqbn,
                 "--build-path", self.build_dir, sketch_path],
                capture_output=True,
                text=True
            )
        
        if run.returncode != 0:
            console.print(f"[bold red]Build failed:[/bold red]\n{run.stderr}")
            return False, current_hash
        
        console.print("[bold green]Build successful.[/bold green]")
        return True, current_hash

    def flash(self, port: str, sketch_path: str) -> bool:
        # arduino-cli upload with --input-dir to find the compiled binary
        with Status("[bold yellow]Flashing...", console=console) as status:
            run = subprocess.run(
                ["arduino-cli", "upload", "--port", port, "--fqbn", self.fqbn,
                 "--input-dir", self.build_dir, sketch_path],
                capture_output=True,
                text=True
            )
        
        if run.returncode != 0:
            console.print(f"[bold red]Flash failed:[/bold red]\n{run.stderr}")
            return False
        
        console.print("[bold green]Flash successful.[/bold green]")
        return True

    def run(self, port: str, sketch_path: str, board_name: str = "") -> tuple[bool, str]:
        built, source_hash = self.build(sketch_path, board_name)
        if not built:
            return False, source_hash
        flashed = self.flash(port, sketch_path)
        return flashed, source_hash

    def get_supported_fqbns(self) -> list[str]:
        return [
            "arduino:avr:uno",
            "arduino:avr:mega",
            "arduino:avr:nano",
            "arduino:renesas_uno:unor4wifi",
        ]