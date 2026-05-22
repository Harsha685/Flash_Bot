from abc import ABC, abstractmethod
import sys

class BaseFlasher(ABC):

    @abstractmethod
    def build(self, sketch_path: str) -> bool:
        """Compile the sketch. Return True on success, False on failure."""
        pass

    @abstractmethod
    def flash(self, port: str, sketch_path: str) -> bool:
        """Flash compiled firmware to the board. Return True on success, False on failure."""
        pass

    @abstractmethod
    def get_supported_fqbns(self) -> list[str]:
        """Return list of fqbns this flasher handles."""
        pass

    def run(self, port: str, sketch_path: str) -> bool:
        if not self.build(sketch_path):
            print("Build failed. Aborting flash.")
            sys.exit(0)
        return self.flash(port, sketch_path)