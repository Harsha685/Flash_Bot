import json
import time
import os
import sys
from detector.usb_listener import start_listener
from detector.device_id import DetectedDevice
from flasher.arduino_flasher import ArduinoFlasher
import pyudev
from detector.device_id import detect_from_udev

# flag to prevent on_device firing multiple times
_flashing = False

def on_device(device):
    global _flashing

    # ignore if already handling a device
    if _flashing:
        return
    _flashing = True

    # load firmware manifest
    with open("config/firmware_manifest.json", "r") as f:
        manifest = json.load(f)

    # get sketches for the detected board
    sketches = manifest.get(device.fqbn, {}).get("sketches", [])

    # no sketches configured for this board
    if not sketches:
        print(f"No sketches configured for {device.name}")
        _flashing = False
        return

    # select sketch — auto if only one, prompt if multiple
    while True:
        if len(sketches) == 1:
            sketch_path = sketches[0]
            break
        else:
            print(f"\nAvailable sketches for {device.name}:")
            for i, sketch in enumerate(sketches):
                print(f"  {i + 1}. {sketch}")
            print(f"  {len(sketches) + 1}. Exit")

            choice = int(input("Select sketch number: "))

            if choice == len(sketches) + 1:
                print("Exiting.")
                os._exit(0)
            elif 1 <= choice <= len(sketches):
                sketch_path = sketches[choice - 1]
                break
            else:
                print("Invalid choice. Try again.")

    # instantiate the correct flasher and run the pipeline
    flasher = ArduinoFlasher(fqbn=device.fqbn)
    flasher.run(device.port, sketch_path)
    os._exit(0)

def check_already_connected():
    context = pyudev.Context()
    for device in context.list_devices(subsystem="tty"):
        if device.get("ID_VENDOR_ID"):
            detected = detect_from_udev(device)
            if detected:
                on_device(detected)

check_already_connected()
start_listener(on_device)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping.")