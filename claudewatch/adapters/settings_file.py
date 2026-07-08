"""Load Settings from config.json (the I/O half of settings).

Reading the file is I/O, so it lives in an adapter; parsing the dict into the
immutable value object is delegated to Settings.from_config. A missing/unreadable
file yields all-defaults.
"""

import json
import os

from ..domain.settings import Settings

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_ROOT, "config.json")


def load_settings(path: str = _CONFIG_PATH) -> Settings:
    try:
        with open(path) as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    return Settings.from_config(cfg)
