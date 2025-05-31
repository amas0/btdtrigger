import itertools as it
import re
import tomllib
from pathlib import Path

from btdtrigger.models import Trigger


def is_valid_regex_pattern(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def parse_triggers_from_config(config_file: Path) -> list[Trigger]:
    """Validates and parses defined triggers from a provided config file

    Expected format is a toml file."""

    def listify(el: str | list[str]) -> list[str]:
        return [el] if isinstance(el, str) else el

    with open(config_file, "rb") as f:
        config = tomllib.load(f)
    triggers = []
    for trigger in config["triggers"]:
        patterns = listify(trigger["device"])
        on_statuses = listify(trigger["status"])
        for pattern, on_status in it.product(patterns, on_statuses):
            if not is_valid_regex_pattern(pattern):
                raise ValueError(f"Invalid regex pattern {pattern} in triggers")
            if on_status not in ("NEW", "DEL"):
                raise ValueError(
                    f"Invalid trigger on clause {on_status}. Must be either NEW or DEL"
                )
            triggers.append(
                Trigger(
                    mac_address_pattern=pattern,
                    on_status=on_status,
                    command=trigger["command"],
                )
            )
    return triggers
