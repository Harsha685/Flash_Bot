import json
import time
import os
import sys
from detector.usb_listener import start_listener
from detector.device_id import DetectedDevice
from flasher.arduino_flasher import ArduinoFlasher
from logger.result_store import ResultStore
import pyudev
from detector.device_id import detect_from_udev, detect_single

_flashing = False

def on_device(device):
    global _flashing

    if _flashing:
        return
    _flashing = True

    try:
        with open("config/firmware_manifest.json", "r") as f:
            manifest = json.load(f)

        sketches = manifest.get(device.fqbn, {}).get("sketches", [])

        if not sketches:
            print(f"No sketches configured for {device.name}")
            return

        while True:
            if len(sketches) == 1:
                sketch_path = sketches[0]
                break
            else:
                print(f"\nAvailable sketches for {device.name}:")
                for i, sketch in enumerate(sketches):
                    print(f"  {i + 1}. {sketch}")
                print(f"  {len(sketches) + 1}. Exit")

                try:
                    choice = int(input("Select sketch number: "))
                except ValueError:
                    print("Invalid input. Enter a number.")
                    continue

                if choice == len(sketches) + 1:
                    print("Exiting.")
                    os._exit(0)
                elif 1 <= choice <= len(sketches):
                    sketch_path = sketches[choice - 1]
                    break
                else:
                    print("Invalid choice. Try again.")

        flasher = ArduinoFlasher(fqbn=device.fqbn)
        success = flasher.run(device.port, sketch_path)

        store = ResultStore()
        device_id = store.log_device(device)
        store.log_flash(device_id, sketch_path, success=success)
        store.close()

        sys.exit(0)

    except Exception as e:
        print(f"Pipeline error: {e}")
    finally:
        _flashing = False

def register_board():
    device = detect_single()
    if not device:
        print("No board detected. Plug in your board and try again.")
        return

    print(f"Detected: {device.name} ({device.fqbn})")

    sketches_dir = "sketches"
    available = []
    for root, dirs, files in os.walk(sketches_dir):
        for f in files:
            if f.endswith(".ino"):
                available.append(os.path.join(root, f))

    if not available:
        print("No sketches found in sketches/")
        return

    print("\nAvailable sketches:")
    for i, s in enumerate(available):
        print(f"  {i + 1}. {s}")

    try:
        choice = int(input("Select sketch number: ")) - 1
    except ValueError:
        print("Invalid input.")
        return

    if not 0 <= choice < len(available):
        print("Invalid choice.")
        return

    sketch_path = available[choice]

    with open("config/firmware_manifest.json", "r") as f:
        manifest = json.load(f)

    if device.fqbn not in manifest:
        manifest[device.fqbn] = {"sketches": []}

    if sketch_path not in manifest[device.fqbn]["sketches"]:
        manifest[device.fqbn]["sketches"].append(sketch_path)

    with open("config/firmware_manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)

    print(f"Registered {device.name} with {sketch_path}")

def check_already_connected():
    context = pyudev.Context()
    for device in context.list_devices(subsystem="tty"):
        if device.get("ID_VENDOR_ID"):
            detected = detect_from_udev(device)
            if detected:
                on_device(detected)

# --- entry point ---

if len(sys.argv) > 1 and sys.argv[1] == "register":
    register_board()
    sys.exit(0)

check_already_connected()
time.sleep(0.5)
start_listener(on_device)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping.")