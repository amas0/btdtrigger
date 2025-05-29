import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class BluetoothDevice:
    mac_address: str
    name: str


@dataclass
class Trigger:
    mac_address_pattern: str
    on: Literal["NEW", "DEL"]
    command: str

    def is_match(self, mac_address: str, status: Literal["NEW", "DEL"]) -> bool:
        """Returns True if the provided mac address and status match the trigger"""
        if status == self.on:
            if re.match(self.mac_address_pattern, mac_address):
                return True
            else:
                return False
        else:
            return False

    def process_command_templates(
        self, mac_address: str, status: Literal["NEW", "DEL"]
    ) -> str:
        return self.command.replace("%address%", mac_address).replace(
            "%status%", status
        )
