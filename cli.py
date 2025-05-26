from pathlib import Path

import typer

from monitor import BluetoothDeviceListener

app = typer.Typer()

CONFIG_DIR = Path.home() / ".config/btdtrigger/"
CONFIG_FILE_NAME = "config.toml"


def main():
    bdl = BluetoothDeviceListener()
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()
    bdl.load_triggers_from_config(config_file=CONFIG_DIR / CONFIG_FILE_NAME)
    bdl.start()
    bdl.listen(run_triggers=True)


if __name__ == "__main__":
    typer.run(main)
