"""Load and access config. Call load() once at startup."""

import yaml
from pathlib import Path


def load(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text())
