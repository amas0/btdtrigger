import os
import shlex
import subprocess
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import btdtrigger.config_parser as config_parser
from btdtrigger.models import BluetoothDevice, Trigger


@dataclass
class ScanLine:
    """Class to capture parsed output of `bluetoothctl`'s scan"""

    status: Literal["NEW", "CHG", "DEL"]
    device_type: Literal["Device", "Controller"]
    mac_address: str
    data: str

    @staticmethod
    def validate_status(status: str) -> Literal["NEW", "CHG", "DEL"]:
        if "NEW" in status:
            return "NEW"
        elif "CHG" in status:
            return "CHG"
        elif "DEL" in status:
            return "DEL"
        else:
            raise ValueError("NEW/CHG/DEL not found in status")

    @staticmethod
    def validate_device_type(device_type: str) -> Literal["Device", "Controller"]:
        if "Device" in device_type:
            return "Device"
        elif "Controller" in device_type:
            return "Controller"
        else:
            raise ValueError("Device/Controller not found in status")

    @classmethod
    def from_raw_line(cls, line: str):
        status, dtype, mac, *data = line.split()
        status = cls.validate_status(status)
        dtype = cls.validate_device_type(dtype)
        return cls(status, dtype, mac, " ".join(data))


@dataclass
class ActiveDevices:
    devices: dict[str, BluetoothDevice] = field(default_factory=dict)

    def add_device(self, device: BluetoothDevice):
        if device.mac_address not in self.devices:
            self.devices[device.mac_address] = device

    def remove_device(self, device: BluetoothDevice):
        if device.mac_address in self.devices:
            del self.devices[device.mac_address]

    def print(self):
        os.system("clear")
        for dev in self.devices.values():
            print(dev)


class BluetoothDeviceListener:
    """This class listens to a scan of nearby Bluetooth devices
    via a `bluetoothctl` subprocess, keeps track of "active"
    Bluetooth devices, and runs commands that are defined as
    triggers on the seen Bluetooth devices"""

    def __init__(self, triggers: list[Trigger] | None = None):
        """Creates a listener to Bluetooth devices with the provided
        defined triggers."""
        self.process = None
        self.running = False
        self.active_devices = ActiveDevices()
        if triggers:
            self.triggers: list[Trigger] = triggers
        else:
            self.triggers = []

    def start(self):
        """Starts the `bluetoothctl` scan if not running"""
        if not self.running:
            self.process = subprocess.Popen(
                ["bluetoothctl", "--timeout", "-1", "scan", "on"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.running = True

    def stop(self):
        """Stops the `bluetoothctl` scan if it is running and the
        proess is active"""
        if self.running and self.process and self.process.poll() is None:
            self.process.kill()
            self.running = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def get_raw_line(self, sleep_ms: int = 5) -> str:
        """Returns the next line from the `bluetoothctl` scan, will
        wait for output."""
        if self.running and self.process and self.process.stdout is not None:
            while (line := self.process.stdout.readline()) is None:
                time.sleep(sleep_ms / 1000)
            return line
        else:
            raise ChildProcessError("No running monitor process found")

    def get_scan_line(self) -> ScanLine:
        """Listens to the `bluetoothctl` scan and returns the next
        valid ScanLine"""
        while line := self.get_raw_line():
            try:
                if line.startswith("[[0;93mCHG[0m]"):  # CHG
                    return ScanLine.from_raw_line(line)
                elif line.startswith("[[0;92mNEW[0m]"):  # NEW
                    return ScanLine.from_raw_line(line)
                elif line.startswith("[[0;91mDEL[0m]"):  # DEL
                    return ScanLine.from_raw_line(line)
                else:
                    continue
            except ValueError:
                warnings.warn(
                    f"Failed attemping to parse scanline from: {line}. Coninuing with next line",
                    UserWarning,
                )
                continue

        raise ValueError("Unable to read scan line")

    def run_triggers(self, device: BluetoothDevice, status: Literal["NEW", "DEL"]):
        """For a given Bluetooth device and status, attempt to run defined triggers"""
        for trigger in self.triggers:
            if trigger.is_match(device.mac_address, status):
                subprocess.run(
                    shlex.split(trigger.process_command_templates(device, status))
                )

    def listen(self):
        """Continuously listen to the scan output of `bluetoothctl` and run
        any matching Triggers if conditions are met"""
        while True:
            changed = False
            sl = self.get_scan_line()
            status = sl.status
            if (sl.device_type != "Device") or (status not in ("NEW", "DEL")):
                continue
            bd = BluetoothDevice(sl.mac_address, sl.data)
            if status == "NEW":
                self.active_devices.add_device(bd)
                changed = True
            elif status == "DEL":
                self.active_devices.remove_device(bd)
                changed = True
            if changed:
                self.run_triggers(bd, status)

    def load_triggers_from_config(self, config_file: Path):
        """Loads Triggers into the listener from a provided config file"""
        self.triggers.extend(config_parser.parse_triggers_from_config(config_file))
