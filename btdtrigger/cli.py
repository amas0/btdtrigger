from pathlib import Path
from typing import Annotated

import typer

from btdtrigger.models import Trigger
from btdtrigger.monitor import BluetoothDeviceListener

app = typer.Typer()

CONFIG_DIR = Path.home() / ".config/btdtrigger/"
CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG = CONFIG_DIR / CONFIG_FILE_NAME


@app.command()
def run(
    config_file: Annotated[
        Path,
        typer.Option(
            "--config", "-c", help="Config file containing trigger definitions"
        ),
    ] = DEFAULT_CONFIG,
):
    bdl = BluetoothDeviceListener()
    bdl.load_triggers_from_config(config_file=config_file)
    bdl.start()
    bdl.listen(run_triggers=True)


@app.command()
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
    if status not in ("NEW", "DEL"):
        raise ValueError("Trigger status must be either 'NEW' or 'DEL'")
    trigger = Trigger(mac_address_pattern=address, on=status, command=command)
    bdl = BluetoothDeviceListener(triggers=[trigger])
    bdl.start()
    bdl.listen(run_triggers=True)


if __name__ == "__main__":
    app()
