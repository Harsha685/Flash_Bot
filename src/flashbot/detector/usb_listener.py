import pyudev
import threading
from flashbot.detector.device_id import detect_from_udev, UnknownBoard, prompt_for_fqbn

def start_listener(on_device, on_unknown=None):
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="tty")

    def _listen():
        for udev_device in iter(monitor.poll, None):
            if udev_device.action == "add":
                result = detect_from_udev(udev_device)
                if isinstance(result, UnknownBoard):
                    if on_unknown:
                        on_unknown(result)
                elif result:
                    print(f"Board detected: {result.name} on {result.port}")
                    on_device(result)

    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()
    return thread