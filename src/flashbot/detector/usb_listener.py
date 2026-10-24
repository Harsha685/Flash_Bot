"""
USB hotplug listener.

Uses udev on Linux for immediate notification and falls back to polling the
serial port list on platforms without pyudev. The callback runs on a
background thread; callers should hand events to the main thread (for
example through a queue) rather than prompting from the callback.
"""

import threading
import time
from typing import Callable

from flashbot.detector.device_id import PortInfo, list_serial_ports, port_info_from_udev

Callback = Callable[[PortInfo], None]


def start_listener(callback: Callback, poll_interval: float = 1.0) -> threading.Thread:
    try:
        import pyudev
    except ImportError:
        return _start_polling(callback, poll_interval)

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="tty")

    def _listen():
        for udev_device in iter(monitor.poll, None):
            if udev_device.action != "add":
                continue
            info = port_info_from_udev(udev_device)
            if info:
                callback(info)

    thread = threading.Thread(target=_listen, name="flashbot-udev", daemon=True)
    thread.start()
    return thread


def _start_polling(callback: Callback, interval: float) -> threading.Thread:
    def _poll():
        known = {p.port for p in list_serial_ports()}
        while True:
            time.sleep(interval)
            current = {p.port: p for p in list_serial_ports()}
            for port in current.keys() - known:
                callback(current[port])
            known = set(current)

    thread = threading.Thread(target=_poll, name="flashbot-poll", daemon=True)
    thread.start()
    return thread
