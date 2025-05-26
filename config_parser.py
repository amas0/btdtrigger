import itertools as it
import re
import tomllib
from pathlib import Path

from models import Trigger


def is_valid_regex_pattern(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def parse_triggers_from_config(config_file: Path) -> list[Trigger]:
    def listify(el: str | list[str]) -> list[str]:
        return [el] if isinstance(el, str) else el

    with open(config_file, "rb") as f:
        config = tomllib.load(f)
    triggers = []
    for trigger in config["triggers"]:
        patterns = listify(trigger["device"])
        ons = listify(trigger["on"])
        for pattern, on in it.product(patterns, ons):
            if not is_valid_regex_pattern(pattern):
                raise ValueError(f"Invalid regex pattern {pattern} in triggers")
            if on not in ("NEW", "DEL"):
                raise ValueError(
                    f"Invalid trigger on clause {on}. Must be either NEW or DEL"
                )
            triggers.append(
                Trigger(mac_address_pattern=pattern, on=on, command=trigger["command"])
            )
    return triggers
