from pathlib import Path
from typing import Annotated

import typer

from btdtrigger.config_parser import is_valid_regex_pattern
from btdtrigger.models import Trigger
from btdtrigger.listener import BluetoothDeviceListener

app = typer.Typer(add_completion=False)

CONFIG_DIR = Path.home() / ".config/btdtrigger/"
CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG = CONFIG_DIR / CONFIG_FILE_NAME


@app.command(help="Run Bluetooth device triggers based on a config file")
def run(
    config_file: Annotated[
        Path,
        typer.Option(
            "--config", "-c", help="Config file containing trigger definitions"
        ),
    ] = DEFAULT_CONFIG,
):
    with BluetoothDeviceListener() as bdl:
        bdl.load_triggers_from_config(config_file=config_file)
        bdl.listen()


@app.command(help="Run a single Bluetooth device trigger from command arguments")
def run_trigger(
    address: Annotated[
        str,
        typer.Option(
            help="Regex pattern to match desired MAC address of triggering bluetooth device."
        ),
    ],
    status: Annotated[
        str,
        typer.Option(
            help="Device status to run the trigger on. Must be 'NEW' or 'DEL'."
        ),
    ],
    command: Annotated[
        str,
        typer.Option(
            help=(
                "Shell command to run when the triggering address and status are matched. "
                "Accepts %address% and %status% templates to inject the device info into the command"
            )
        ),
    ],
):
    if not is_valid_regex_pattern(address):
        raise ValueError("Provided address regex pattern is invalid")
    if status not in ("NEW", "DEL"):
        raise ValueError("Trigger status must be either 'NEW' or 'DEL'")
    trigger = Trigger(mac_address_pattern=address, on_status=status, command=command)
    with BluetoothDeviceListener(triggers=[trigger]) as bdl:
        bdl.listen()


if __name__ == "__main__":
    app()
