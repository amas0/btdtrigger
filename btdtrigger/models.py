import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class BluetoothDevice:
    mac_address: str
    name: str


@dataclass
class Trigger:
    """Object defining a trigger, which is a command that is
    run when a Bluetooth device with a mac address that
    matches a given regex pattern and scan status.

    For example, a trigger that runs `echo hello` whenever
    a new device with a mac address that starts with "AA" is
    seen would be:

    ```
    Trigger("AA.*", "NEW", "echo hello")
    ```

    The command support templates for three properties,
    the devices mac address `%address%`, the status
    `%status%, and the device name `%name%`.

    So `Trigger("AA.*", "NEW", "echo hello %address%")`
    hitting on a device with mac address "AA:BB:CC:DD:EE"
    would echo `hello AA:BB:CC:DD:EE`.
    """

    mac_address_pattern: str
    on_status: Literal["NEW", "DEL"]
    command: str

    def is_match(self, mac_address: str, status: Literal["NEW", "DEL"]) -> bool:
        """Returns True if the provided mac address and status match the trigger"""
        if status == self.on_status:
            if re.match(self.mac_address_pattern, mac_address, flags=re.IGNORECASE):
                return True
            else:
                return False
        else:
            return False

    def process_command_templates(
        self, device: BluetoothDevice, status: Literal["NEW", "DEL"]
    ) -> str:
        """Processes templates in the command via string replacement"""
        templated = (
            self.command.replace("%address%", device.mac_address)
            .replace("%status%", status)
            .replace("%name%", device.name)
        )
        return templated
