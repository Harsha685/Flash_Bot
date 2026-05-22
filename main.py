import json
import time
from detector.usb_listener import start_listener
from detector.device_id import detect_from_udev, prompt_for_fqbn, UnknownBoard
from flasher import get_flasher
from logger.result_store import init_db, save_result
from tester.test_cases import get_tests_for_sketch
from tester.test_runner import TestRunner
from config.sketch_scanner import update_manifest
import pyudev

_flashing = False
_shutdown = False
_flash_cooldown = {}


def _pick_sketch(device, sketches):
    if len(sketches) == 1:
        return sketches[0]
    while True:
        print(f"\nAvailable sketches for {device.name}:")
        for i, sketch in enumerate(sketches):
            print(f"  {i + 1}. {sketch}")
        print(f"  {len(sketches) + 1}. Exit")
        try:
            choice = int(input("Select sketch number: "))
        except ValueError:
            print("Invalid input.")
            continue
        if choice == len(sketches) + 1:
            return None
        if 1 <= choice <= len(sketches):
            return sketches[choice - 1]
        print("Invalid choice.")


def _run_pipeline(device):
    global _flash_cooldown
    with open("config/firmware_manifest.json", "r") as f:
        manifest = json.load(f)
    sketches = manifest.get(device.fqbn, {}).get("sketches", [])
    if not sketches:
        print(f"No sketches configured for {device.name}")
        return

    while True:
        sketch_path = _pick_sketch(device, sketches)
        if sketch_path is None:
            print("Returning to listener.")
            break

        flasher = get_flasher(device.fqbn)
        try:
            ok, source_hash = flasher.run(device.port, sketch_path, device.name)
            flash_status = "success" if ok else "failed"
            flash_error = None if ok else "Build or flash step failed"
            print(f"[FLASH] {'OK' if ok else 'FAIL'}")
        except Exception as e:
            flash_status = "failed"
            flash_error = str(e)
            source_hash = None
            print(f"[FLASH ERROR] {e}")

        save_result(device.name, device.fqbn, device.port, sketch_path,
                    flash_status, flash_error, source_hash)
        print(f"[DB] Logged: {flash_status}")

        if flash_status == "success":
            _flash_cooldown[device.serial_number or device.port] = time.time()
            tests = get_tests_for_sketch(sketch_path)
            if tests:
                runner = TestRunner(device.port)
                try:
                    all_passed, results = runner.run_all(tests)
                    print(f"[TEST] {'All passed' if all_passed else 'Some failed'}")
                    for r in results:
                        status = "PASS" if r["passed"] else "FAIL"
                        print(f"       {r['name']}: {status}")
                except Exception as e:
                    print(f"[TEST ERROR] {e}")

        again = input("\nFlash another sketch to this board? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print("Returning to listener.")
            break


def on_device(device):
    global _flashing
    if _flashing:
        return
    _flashing = True
    try:
        _run_pipeline(device)
    finally:
        _flashing = False


def handle_unknown(unknown):
    """Called when a USB device is detected but not in BOARD_TABLE."""
    global _flashing
    if _flashing:
        return
    _flashing = True
    try:
        device = prompt_for_fqbn(unknown)
        if device:
            print(f"[REGISTERED] {device.name} ({device.fqbn})")
            # Immediately run pipeline on it since it's already plugged in
            _run_pipeline(device)
    finally:
        _flashing = False


def check_already_connected():
    context = pyudev.Context()
    for device in context.list_devices(subsystem="tty"):
        if device.get("ID_VENDOR_ID"):
            result = detect_from_udev(device)
            if isinstance(result, UnknownBoard):
                handle_unknown(result)
            elif result:
                on_device(result)


if __name__ == "__main__":
    init_db()
    update_manifest()
    check_already_connected()
    start_listener(on_device, on_unknown=handle_unknown)

    print("[READY] Listening for USB devices... (Ctrl+C to quit)")
    try:
        while not _shutdown:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    print("Stopping.")