import os
import socket
import subprocess

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

_CONFIG_CACHE = None


def _load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        import yaml
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
        _CONFIG_CACHE = yaml.safe_load(open(cfg_path))
    except Exception:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


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
    except (OSError, TimeoutError):
        return False


def _group_status(containers: list, container_links: dict | None = None) -> dict:
    """Check each group container — returns status string + per-container details."""
    if container_links is None:
        container_links = {}
    if not containers:
        return {"status": "Offline (0/0)", "containers": []}
    try:
        result_names = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        running = set(result_names.stdout.strip().splitlines())

        # Get ports for running containers
        result_ports = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=5
        )
        port_map = {}
        for line in result_ports.stdout.strip().splitlines():
            if not line or "\t" not in line:
                continue
            parts = line.split("\t", 1)
            port_map[parts[0]] = parts[1] if len(parts) > 1 and parts[1] else "—"

        container_details = []
        for c in containers:
            online = c in running
            ports = port_map.get(c, "—") if online else ""
            short_name = c.replace("passive-income-", "")
            link_url = container_links.get(short_name, "")
            container_details.append({
                "name": c,
                "online": online,
                "ports": ports,
                "link_url": link_url,
            })

        total = len(containers)
        on = sum(1 for d in container_details if d["online"])
        if on == total:
            status = f"Online ({on}/{total})"
        elif on > 0:
            status = f"Partial ({on}/{total})"
        else:
            status = f"Offline (0/{total})"

        return {"status": status, "containers": container_details}
    except Exception:
        return {"status": "Unknown", "containers": []}


def get_service_status() -> dict:
    cfg = _load_config()
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
        check_type = info.get("check", "port")
        group_data = {"containers": []}

        if check_type == "group":
            group_containers = info.get("group_containers", [])
            links = info.get("container_links", {})
            group_data = _group_status(group_containers, container_links=links)
            status = group_data["status"]
        elif port:
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
            "check_type": check_type,
            "group_entries": [
                {**c, "short_name": c["name"].replace("passive-income-", "")}
                for c in group_data.get("containers", [])
            ] if check_type == "group" else [],
            "port": port if port else None,
        }
    return services_map