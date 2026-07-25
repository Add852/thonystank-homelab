import os

SERVICE_ICONS = {
    "hermes": "fa-robot",
    "immich": "fa-images",
    "mnemosyne": "fa-brain",
    "proxmox": "fa-server",
    "syncthing": "fa-sync",
    "9router": "fa-route",
    "openai-oauth": "fa-lock",
    "headroom": "fa-shield-halved",
    "dashboard": "fa-gauge-high",
    "codex": "fa-terminal",
}


def _get_icon(name: str, display_name: str | None = None) -> str:
    key = name.lower()
    if key in SERVICE_ICONS:
        return SERVICE_ICONS[key]
    if display_name and display_name.lower().split()[0] in SERVICE_ICONS:
        return SERVICE_ICONS[display_name.lower().split()[0]]
    return "fa-cube"


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    if port == 8006 and host == "127.0.0.1":
        host = "192.168.1.16"
    try:
        with __import__("socket").create_connection((host, port), timeout=3):
            return True
    except (OSError, TimeoutError):
        return False


def get_service_status() -> dict:
    cfg = {}
    try:
        import yaml
        cfg = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")))
    except Exception:
        pass

    services_cfg = cfg.get("services", {})

    if not isinstance(services_cfg, dict):
        return {}

    services_map = {}
    for name, info in services_cfg.items():
        key = name.lower()
        port = info.get("port", 0)
        url = info.get("url", "")
        public_url = info.get("public_url", "")
        display_name = info.get("display_name", name)
        icon = info.get("icon", "fa-cube")
        description = info.get("description", "")
        tailscale_only = info.get("tailscale_only", False)
        icon_url = info.get("icon_url", "")

        if port:
            host = info.get("host", "127.0.0.1")
            status = "Online" if _port_open(port, host) else "Offline"
        else:
            status = "Offline"

        services_map[key] = {
            "display_name": display_name,
            "icon": icon if icon.startswith("fa-") else _get_icon(key, display_name),
            "icon_url": icon_url,
            "status": status,
            "description": description,
            "url": url,
            "public_url": public_url,
            "tailscale_only": tailscale_only,
        }
    return services_map