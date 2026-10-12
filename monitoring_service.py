import os
import socket
import time
from urllib.parse import urlparse

import httpx
from concurrent.futures import ThreadPoolExecutor

_CONFIG_CACHE = None

def _load_config():
    """Fallback loader for standalone use; main.py passes its CONFIG explicitly."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        from config import load_config
        _CONFIG_CACHE = load_config()
    except Exception:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE

def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except (OSError, TimeoutError):
        return False

def _url_ok(url: str) -> bool:
    """HTTP check; verify=False because homelab services often use self-signed certs."""
    try:
        r = httpx.head(url, timeout=3, follow_redirects=True, verify=False)
        if r.status_code < 500:
            return True
    except Exception:
        pass
    try:
        r = httpx.get(url, timeout=3, follow_redirects=True, verify=False)
        return r.status_code < 500
    except Exception:
        return False

def _check_service(info: dict) -> bool:
    """HTTP URL check first (accurate across hosts/proxies), TCP port as fallback.
    Runs in a worker thread."""
    urls = [u for u in (info.get("url"), info.get("public_url")) if u]
    for u in urls:
        if _url_ok(u):
            return True
    port = info.get("port", 0)
    if not port:
        return False
    host = info.get("host")
    if not host:
        for u in urls:
            host = urlparse(u).hostname
            if host:
                break
    return _port_open(port, host or "127.0.0.1")

# Status cache: port probes are slow; reuse results for a short TTL.
# ponytail: no stampede lock — a concurrent double-recompute is harmless at this scale.
_STATUS_TTL = 30  # seconds
_status_cache: dict = {"ts": 0.0, "data": None}

def get_service_status(cfg: dict | None = None) -> dict:
    """Check each service's port liveness (concurrently) and return display info."""
    cfg = cfg if cfg is not None else _load_config()
    services_cfg = cfg.get("services", {})
    if not isinstance(services_cfg, dict):
        return {}

    now = time.time()
    if _status_cache["data"] is not None and now - _status_cache["ts"] < _STATUS_TTL:
        return _status_cache["data"]

    # Run all port checks concurrently instead of serially
    with ThreadPoolExecutor(max_workers=max(1, min(len(services_cfg), 16))) as pool:
        futures = {name: pool.submit(_check_service, info)
                   for name, info in services_cfg.items()}

    services_map = {}
    for name, info in services_cfg.items():
        port = info.get("port", 0)
        services_map[name.lower()] = {
            "display_name": info.get("display_name", name),
            "icon": info.get("icon", "fa-cube"),
            "icon_url": info.get("icon_url", ""),
            "status": "Online" if futures[name].result() else "Offline",
            "description": info.get("description", ""),
            "url": info.get("url", ""),
            "public_url": info.get("public_url", ""),
            "port": port or None,
        }

    _status_cache["ts"] = time.time()
    _status_cache["data"] = services_map
    return services_map
