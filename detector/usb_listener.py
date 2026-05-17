import pyudev
import threading
from detector.device_id import detect_from_udev

def start_listener(callback):
    context = pyudev.Context()
    monitor  = pyudev.Monitor.from_netlink(context)

    # only react to tty devices — ignores everything else on the bus
    monitor.filter_by(subsystem="tty")

    def _listen():
        for udev_device in iter(monitor.poll, None):
            # only care about plug-in events, not removals
            if udev_device.action == "add":
                device = detect_from_udev(udev_device)
                if device:
                    print(f"Board detected: {device.name} on {device.port}")
                    callback(device)

    # run in a daemon thread so it doesn't block main
    listener_thread = threading.Thread(target=_listen, daemon=True)
    listener_thread.start()
    return listener_thread

if __name__ == "__main__":
    import time

    def on_device(device):
        print("Device found:", device)

    thread = start_listener(on_device)

    # keep main alive so the daemon thread keeps running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping listener")