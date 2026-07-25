import os
import yaml

_CONFIG: dict = {}
_MTIME: float = 0


def get_config() -> dict:
    global _CONFIG, _MTIME
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    mtime = os.path.getmtime(path)
    if not _CONFIG or mtime > _MTIME:
        with open(path) as f:
            _CONFIG = yaml.safe_load(f) or {}
        _MTIME = mtime
    return _CONFIG
