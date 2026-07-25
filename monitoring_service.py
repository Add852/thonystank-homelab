import os
import socket
import subprocess

SERVICE_ICONS = {
    "hermes": "fa-robot",
    "immich": "fa-images",
    "mnemosyne": "fa-brain",
    "proxmox": "fa-server",
    "syncthing": "fa-sync",
    "openai-oauth": "fa-lock",
    "headroom": "fa-shield-halved",
    "dashboard": "fa-gauge-high",
    "codex": "fa-terminal",
}

SERVICE_PORTS = {
    "hermes": 9119,
    "immich": 2283,
    "mnemosyne": 8765,
    "syncthing": 8384,
    "headroom": 20128,
    "dashboard": 8080,
}

SERVICE_DESCRIPTIONS = {
    "hermes": "AI agent",
    "immich": "Photo backup",
    "mnemosyne": "Memory dashboard",
    "syncthing": "File sync",
    "proxmox": "VM management",
    "headroom": "AI compression proxy",
    "dashboard": "Server dashboard",
}

SERVICE_LAN_URLS = {
    "hermes": "http://192.168.1.17:9119",
    "immich": "http://192.168.1.17:2283",
    "mnemosyne": "http://192.168.1.17:8765",
    "syncthing": "http://192.168.1.17:8384",
    "proxmox": "http://192.168.1.16:8006",
}

SERVICE_PUBLIC_URLS = {
    "hermes": "https://hermes.thonystank.dpdns.org",
    "immich": "https://photos.thonystank.dpdns.org",
    "mnemosyne": "https://memory.thonystank.dpdns.org",
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
        with socket.create_connection((host, port), timeout=3):
            return True
    except (OSError, socket.timeout):
        return False


def _process_exists(process_name: str) -> bool:
    try:
        r = subprocess.run(["pgrep", "-u", os.environ.get("USER", ""), process_name],
                           capture_output=True, timeout=5, text=True)
        return bool(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_service_status() -> dict:
    services_list = [
        "hermes", "immich", "mnemosyne", "syncthing",
        "proxmox",
    ]

    try:
        import yaml
        cfg = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")))
        svc_list = cfg.get("services")
        if isinstance(svc_list, list):
            for name in svc_list:
                n = name.lower()
                if n not in services_list:
                    services_list.append(n)
    except Exception:
        pass

    result = {}
    for name in services_list:
        display_name = {
            "hermes": "Hermes Agent",
            "mnemosyne": "Memory (mnemosyne)",
            "proxmox": "Proxmox",
        }.get(name, name.capitalize())

        url = SERVICE_LAN_URLS.get(name) or ""
        public_url = SERVICE_PUBLIC_URLS.get(name) or ""

        if name == "proxmox":
            status = "Online" if _port_open(8006, "192.168.1.16") else "Offline"
        elif name in SERVICE_PORTS:
            status = "Online" if _port_open(SERVICE_PORTS[name]) else "Offline"
        else:
            status = "Offline"

        result[name] = {
            "display_name": display_name,
            "icon": _get_icon(name, display_name),
            "status": status,
            "description": SERVICE_DESCRIPTIONS.get(name, ""),
            "url": url,
            "public_url": public_url,
        }

    return result
