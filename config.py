"""Single config loader: .env → config.yaml with ${VAR} expansion.

Device-specific values (paths, IPs) go in .env as VAR=value and are referenced
from config.yaml as ${VAR}. config.yaml stays portable and syncable;
.env is gitignored and differs per device.
"""
import os
import re

import yaml

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _load_dotenv(path: str = None) -> None:
    """Tiny .env loader — KEY=VALUE lines, # comments, quotes stripped.
    Does not override variables already in the environment."""
    path = path or os.path.join(_BASE_DIR, ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


def _expand(value):
    """Expand ${VAR} references. A string that is exactly one reference resolves
    to the env value (or None if unset); embedded references resolve inline."""
    if isinstance(value, str):
        m = _ENV_RE.fullmatch(value.strip())
        if m:
            return os.environ.get(m.group(1))
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config() -> dict:
    _load_dotenv()
    path = os.environ.get("SERVER_DASHBOARD_CONFIG", os.path.join(_BASE_DIR, "config.yaml"))
    with open(path) as f:
        return _expand(yaml.safe_load(f) or {})
