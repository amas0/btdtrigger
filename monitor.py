import itertools as it
import os
import re
import shlex
import subprocess
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class ScanLine:
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
class BluetoothDevice:
    mac_address: str
    name: str


@dataclass
class Trigger:
    mac_address: str
    on: Literal["NEW", "DEL"]
    command: str


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
    def __init__(self, triggers: list[Trigger] | None = None):
        self.process = None
        self.running = False
        self.active_devices = ActiveDevices()
        if triggers:
            self.triggers: list[Trigger] = triggers
        else:
            self.triggers = []

    def start(self):
        if not self.running:
            self.process = subprocess.Popen(
                ["bluetoothctl", "--timeout", "-1", "scan", "on"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.running = True

    def stop(self):
        if self.running and self.process and self.process.poll() is None:
            self.process.kill()
            self.running = False

    def get_raw_line(self, sleep_ms: int = 5) -> str:
        if self.running and self.process and self.process.stdout is not None:
            while (line := self.process.stdout.readline()) is None:
                time.sleep(sleep_ms / 1000)
            return line
        else:
            raise ChildProcessError("No running monitor process found")

    def get_scan_line(self) -> ScanLine:
        while line := self.get_raw_line():
            if line.startswith("[[0;93mCHG[0m]"):  # CHG
                return ScanLine.from_raw_line(line)
            elif line.startswith("[[0;92mNEW[0m]"):  # NEW
                return ScanLine.from_raw_line(line)
            elif line.startswith("[[0;91mDEL[0m]"):  # DEL
                return ScanLine.from_raw_line(line)
            else:
                continue
        raise ValueError("Unable to read scan line")

    def run_triggers(self, mac_address: str, status: Literal["NEW", "DEL"]):
        for trigger in self.triggers:
            if (trigger.mac_address == mac_address) and (trigger.on == status):
                subprocess.run(shlex.split(trigger.command))

    def listen(self, print_devices: bool = False, run_triggers: bool = False):
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
                if print_devices:
                    self.active_devices.print()
                if run_triggers:
                    self.run_triggers(bd.mac_address, status)

    @staticmethod
    def is_valid_mac_address(address: str) -> bool:
        pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
        return re.fullmatch(pattern, address) is not None

    def load_triggers_from_config(self, config_file: Path):
        def listify(el: str | list[str]) -> list[str]:
            return [el] if isinstance(el, str) else el

        with open(config_file, "rb") as f:
            config = tomllib.load(f)
        triggers = []
        for trigger in config["triggers"]:
            devices = listify(trigger["device"])
            ons = listify(trigger["on"])
            for device, on in it.product(devices, ons):
                if not self.is_valid_mac_address(device):
                    raise ValueError(f"Invalid MAC address {device} in triggers")
                if on not in ("NEW", "DEL"):
                    raise ValueError(
                        f"Invalid trigger on clause {on}. Must be either NEW or DEL"
                    )
                triggers.append(
                    Trigger(mac_address=device, on=on, command=trigger["command"])
                )
        self.triggers.extend(triggers)
