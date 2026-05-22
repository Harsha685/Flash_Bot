import serial
import serial.tools.list_ports
import time

class SerialComm:
    def __init__(self, port: str, baud: int = 9600, timeout: float = 2.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial = None

    def connect(self, retries: int = 3, delay: float = 1.0):
        available = self.list_ports()
        if self.port not in available:
            raise ConnectionError(
                f"Port {self.port} not found.\nAvailable ports: {available}"
            )
        for attempt in range(retries):
            try:
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    timeout=self.timeout
                )
                time.sleep(2)
                return
            except serial.SerialException as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    raise ConnectionError(
                        f"Could not open {self.port} after {retries} attempts: {e}"
                    )

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

    def send(self, command: str) -> str:
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            self.serial.reset_input_buffer()
            self.serial.write((command + '\n').encode('utf-8'))
            response = self.serial.readline()
            if not response:
                raise TimeoutError(f"No response to '{command}' within {self.timeout}s")
            return response.decode('utf-8', errors='replace').strip()
        except serial.SerialException as e:
            try:
                time.sleep(1)
                self.connect()
                return self.send(command)
            except Exception:
                raise ConnectionError(f"Board disconnected and reconnect failed: {e}")

    def is_connected(self) -> bool:
        return self.serial is not None and self.serial.is_open

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    @staticmethod
    def list_ports():
        return [p.device for p in serial.tools.list_ports.comports()]