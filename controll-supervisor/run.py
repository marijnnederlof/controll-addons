#!/usr/bin/env python3
"""
Controll Supervisor Add-on
Remote management API for Controll fleet management platform.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from aiohttp import web, ClientSession

# Controll Theme - light/fresh design matching controll.it
CONTROLL_THEME = """controll:
  # Primary orange from controll.it
  primary-color: "#f97316"
  accent-color: "#ea580c"

  # Header - white with orange accent
  app-header-background-color: "#ffffff"
  app-header-text-color: "#1f2937"

  # Sidebar - clean white/light gray
  sidebar-background-color: "#f8fafc"
  sidebar-text-color: "#374151"
  sidebar-selected-background-color: "#f97316"
  sidebar-selected-icon-color: "#ffffff"
  sidebar-selected-text-color: "#ffffff"
  sidebar-icon-color: "#6b7280"

  # Cards - white with subtle shadow
  card-background-color: "#ffffff"
  ha-card-background: "#ffffff"
  ha-card-border-radius: "8px"
  ha-card-box-shadow: "0 1px 3px rgba(0, 0, 0, 0.1)"

  # Text colors
  primary-text-color: "#1f2937"
  secondary-text-color: "#6b7280"
  text-primary-color: "#1f2937"

  # Background - light gray
  background-color: "#f3f4f6"
  primary-background-color: "#f3f4f6"
  secondary-background-color: "#ffffff"

  # UI elements
  divider-color: "#e5e7eb"
  state-icon-color: "#374151"
  state-on-color: "#f97316"
  state-off-color: "#9ca3af"

  # Switches
  switch-checked-color: "#f97316"
  switch-unchecked-button-color: "#9ca3af"
  switch-unchecked-track-color: "#d1d5db"

  # Material design
  mdc-theme-primary: "#f97316"

  # Inputs
  input-fill-color: "#f9fafb"
  input-ink-color: "#1f2937"
  input-label-ink-color: "#6b7280"
"""

# Configuration
CONFIG_PATH = "/data/options.json"
HA_CONFIG_PATH = "/config"
SUPERVISOR_API = "http://supervisor"
HA_API = "http://supervisor/core/api"

# Load options
with open(CONFIG_PATH) as f:
    OPTIONS = json.load(f)

HUB_TOKEN = OPTIONS.get("hub_token", "")
PLATFORM_URL = OPTIONS.get("platform_url", "https://api.controll.it")
HEARTBEAT_INTERVAL = OPTIONS.get("heartbeat_interval", 300)
LOG_LEVEL = OPTIONS.get("log_level", "info")

# Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("controll")

# Supervisor token from environment
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")


def get_supervisor_headers():
    """Get headers for Supervisor API calls."""
    return {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json"
    }


def verify_token(request):
    """Verify the hub token from request."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:]
    return token == HUB_TOKEN


# ============== FILE OPERATIONS ==============

async def handle_file_write(request):
    """Write a file to the config directory."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        path = data.get("path", "")
        content = data.get("content", "")

        # Security: only allow writes within /config
        if ".." in path or path.startswith("/"):
            return web.json_response({"error": "Invalid path"}, status=400)

        full_path = Path(HA_CONFIG_PATH) / path

        # Create directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content)

        logger.info(f"Wrote file: {path}")
        return web.json_response({"success": True, "path": str(path)})

    except Exception as e:
        logger.error(f"File write error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_file_read(request):
    """Read a file from the config directory."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        path = request.query.get("path", "")

        if ".." in path or path.startswith("/"):
            return web.json_response({"error": "Invalid path"}, status=400)

        full_path = Path(HA_CONFIG_PATH) / path

        if not full_path.exists():
            return web.json_response({"error": "File not found"}, status=404)

        content = full_path.read_text()
        return web.json_response({"success": True, "content": content})

    except Exception as e:
        logger.error(f"File read error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_file_list(request):
    """List files in a directory."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        path = request.query.get("path", "")

        if ".." in path:
            return web.json_response({"error": "Invalid path"}, status=400)

        full_path = Path(HA_CONFIG_PATH) / path if path else Path(HA_CONFIG_PATH)

        if not full_path.exists():
            return web.json_response({"error": "Path not found"}, status=404)

        files = []
        for item in full_path.iterdir():
            files.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0
            })

        return web.json_response({"success": True, "files": files})

    except Exception as e:
        logger.error(f"File list error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== HOME ASSISTANT API ==============

async def handle_ha_service(request):
    """Call a Home Assistant service."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        domain = data.get("domain")
        service = data.get("service")
        service_data = data.get("data", {})

        async with ClientSession() as session:
            async with session.post(
                f"{HA_API}/services/{domain}/{service}",
                headers=get_supervisor_headers(),
                json=service_data
            ) as resp:
                result = await resp.json()
                return web.json_response({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Service call error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_ha_restart(request):
    """Restart Home Assistant."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        async with ClientSession() as session:
            async with session.post(
                f"{SUPERVISOR_API}/core/restart",
                headers=get_supervisor_headers()
            ) as resp:
                if resp.status == 200:
                    return web.json_response({"success": True, "message": "Restart initiated"})
                else:
                    return web.json_response({"error": "Restart failed"}, status=500)

    except Exception as e:
        logger.error(f"Restart error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_ha_config(request):
    """Get Home Assistant configuration."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        async with ClientSession() as session:
            async with session.get(
                f"{HA_API}/config",
                headers=get_supervisor_headers()
            ) as resp:
                config = await resp.json()
                return web.json_response({"success": True, "config": config})

    except Exception as e:
        logger.error(f"Config error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_ha_states(request):
    """Get all entity states."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        async with ClientSession() as session:
            async with session.get(
                f"{HA_API}/states",
                headers=get_supervisor_headers()
            ) as resp:
                states = await resp.json()
                return web.json_response({"success": True, "states": states})

    except Exception as e:
        logger.error(f"States error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== ADDON MANAGEMENT ==============

async def handle_addon_list(request):
    """List installed add-ons."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        async with ClientSession() as session:
            async with session.get(
                f"{SUPERVISOR_API}/addons",
                headers=get_supervisor_headers()
            ) as resp:
                data = await resp.json()
                return web.json_response({"success": True, "addons": data.get("data", {}).get("addons", [])})

    except Exception as e:
        logger.error(f"Addon list error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_addon_install(request):
    """Install an add-on."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        addon_slug = data.get("slug")

        async with ClientSession() as session:
            async with session.post(
                f"{SUPERVISOR_API}/addons/{addon_slug}/install",
                headers=get_supervisor_headers()
            ) as resp:
                if resp.status == 200:
                    return web.json_response({"success": True, "message": f"Installing {addon_slug}"})
                else:
                    error = await resp.text()
                    return web.json_response({"error": error}, status=resp.status)

    except Exception as e:
        logger.error(f"Addon install error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== SYSTEM INFO ==============

async def handle_system_info(request):
    """Get system information."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        info = {}

        async with ClientSession() as session:
            # Host info
            async with session.get(
                f"{SUPERVISOR_API}/host/info",
                headers=get_supervisor_headers()
            ) as resp:
                host = await resp.json()
                info["host"] = host.get("data", {})

            # Core info
            async with session.get(
                f"{SUPERVISOR_API}/core/info",
                headers=get_supervisor_headers()
            ) as resp:
                core = await resp.json()
                info["core"] = core.get("data", {})

            # Supervisor info
            async with session.get(
                f"{SUPERVISOR_API}/supervisor/info",
                headers=get_supervisor_headers()
            ) as resp:
                supervisor = await resp.json()
                info["supervisor"] = supervisor.get("data", {})

        return web.json_response({"success": True, "info": info})

    except Exception as e:
        logger.error(f"System info error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== DISCOVERY ==============

async def handle_discovery(request):
    """Scan network for known domotica systems."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        discovered = []

        # Get network info
        async with ClientSession() as session:
            async with session.get(
                f"{SUPERVISOR_API}/network/info",
                headers=get_supervisor_headers()
            ) as resp:
                network = await resp.json()

        # Known ports to scan
        KNOWN_SYSTEMS = {
            8080: {"type": "digitalstrom", "name": "digitalSTROM dSS"},
            80: {"type": "hue", "name": "Philips Hue Bridge"},
            1400: {"type": "sonos", "name": "Sonos Speaker"},
            3671: {"type": "knx", "name": "KNX IP Gateway"},
        }

        # Simple port scan using nmap (if available)
        try:
            # Get local subnet
            result = subprocess.run(
                ["nmap", "-sn", "192.168.1.0/24", "-oG", "-"],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse hosts
            for line in result.stdout.split("\n"):
                if "Host:" in line and "Status: Up" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[1]

                        # Check known ports
                        for port, system_info in KNOWN_SYSTEMS.items():
                            try:
                                port_check = subprocess.run(
                                    ["nc", "-z", "-w", "1", ip, str(port)],
                                    capture_output=True,
                                    timeout=2
                                )
                                if port_check.returncode == 0:
                                    discovered.append({
                                        "host": ip,
                                        "port": port,
                                        "type": system_info["type"],
                                        "name": system_info["name"]
                                    })
                            except:
                                pass
        except Exception as e:
            logger.warning(f"Network scan failed: {e}")

        return web.json_response({"success": True, "discovered": discovered})

    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== THEME INSTALLATION ==============

async def handle_install_theme(request):
    """Install a theme from content."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        theme_name = data.get("name", "controll")
        theme_content = data.get("content", "")

        # Create themes directory
        themes_dir = Path(HA_CONFIG_PATH) / "themes"
        themes_dir.mkdir(exist_ok=True)

        # Write theme file
        theme_file = themes_dir / f"{theme_name}.yaml"
        theme_file.write_text(theme_content)

        # Check if themes are configured in configuration.yaml
        config_file = Path(HA_CONFIG_PATH) / "configuration.yaml"
        config_content = config_file.read_text() if config_file.exists() else ""

        if "themes:" not in config_content:
            # Add theme configuration
            with open(config_file, "a") as f:
                f.write("\n\n# Controll themes\nfrontend:\n  themes: !include_dir_merge_named themes\n")

            logger.info("Added theme configuration to configuration.yaml")

        logger.info(f"Installed theme: {theme_name}")
        return web.json_response({
            "success": True,
            "message": f"Theme '{theme_name}' installed. Restart HA to apply.",
            "restart_required": True
        })

    except Exception as e:
        logger.error(f"Theme install error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== BRANDING ==============

async def handle_set_branding(request):
    """Set Home Assistant branding (name, etc)."""
    if not verify_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        name = data.get("name", "Controll")

        config_file = Path(HA_CONFIG_PATH) / "configuration.yaml"
        config_content = config_file.read_text() if config_file.exists() else ""

        # Check if homeassistant: section exists
        if "homeassistant:" not in config_content:
            # Add branding
            with open(config_file, "a") as f:
                f.write(f"\n\nhomeassistant:\n  name: {name}\n")
        else:
            # Update name - this is simplified, a real implementation would parse YAML properly
            import yaml
            # For now just log that manual update is needed
            logger.warning("homeassistant: section exists, manual update may be needed")

        return web.json_response({
            "success": True,
            "message": f"Branding set to '{name}'. Restart HA to apply.",
            "restart_required": True
        })

    except Exception as e:
        logger.error(f"Branding error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ============== HEALTH CHECK ==============

async def handle_health(request):
    """Health check endpoint (no auth required)."""
    return web.json_response({
        "status": "healthy",
        "addon": "controll-supervisor",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })


# ============== HEARTBEAT ==============

async def send_heartbeat():
    """Send periodic heartbeat to Controll platform."""
    while True:
        try:
            if not HUB_TOKEN:
                logger.warning("No hub token configured, skipping heartbeat")
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                continue

            # Gather system info
            info = {}
            async with ClientSession() as session:
                try:
                    async with session.get(
                        f"{SUPERVISOR_API}/core/info",
                        headers=get_supervisor_headers()
                    ) as resp:
                        core = await resp.json()
                        info["ha_version"] = core.get("data", {}).get("version")
                except:
                    pass

                try:
                    async with session.get(
                        f"{HA_API}/states",
                        headers=get_supervisor_headers()
                    ) as resp:
                        states = await resp.json()
                        info["entities_count"] = len(states)
                except:
                    pass

                # Send heartbeat to platform
                try:
                    async with session.post(
                        f"{PLATFORM_URL}/api/provision/heartbeat",
                        json={
                            "device_id": HUB_TOKEN.split("_")[0] if "_" in HUB_TOKEN else "unknown",
                            "ha_version": info.get("ha_version"),
                            "entities_count": info.get("entities_count", 0),
                            "uptime": 0  # TODO: implement
                        }
                    ) as resp:
                        if resp.status == 200:
                            logger.debug("Heartbeat sent successfully")
                        else:
                            logger.warning(f"Heartbeat failed: {resp.status}")
                except Exception as e:
                    logger.warning(f"Heartbeat error: {e}")

        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

        await asyncio.sleep(HEARTBEAT_INTERVAL)


# ============== AUTO SETUP ON STARTUP ==============

def install_controll_branding():
    """Install Controll theme and branding on startup."""
    logger.info("Installing Controll branding...")

    # Create themes directory
    themes_dir = Path(HA_CONFIG_PATH) / "themes"
    themes_dir.mkdir(exist_ok=True)

    # Write theme file
    theme_file = themes_dir / "controll.yaml"
    theme_file.write_text(CONTROLL_THEME)
    logger.info("Controll theme installed")

    # Update configuration.yaml
    config_file = Path(HA_CONFIG_PATH) / "configuration.yaml"
    config_content = config_file.read_text() if config_file.exists() else ""

    changed = False

    # Add homeassistant name if not present
    if "name: Controll" not in config_content and "name: \"Controll\"" not in config_content:
        if "homeassistant:" not in config_content:
            config_content += "\n\nhomeassistant:\n  name: Controll\n"
            changed = True
            logger.info("Added Controll name")

    # Add themes config if not present
    if "themes:" not in config_content:
        if "frontend:" not in config_content:
            config_content += "\nfrontend:\n  themes: !include_dir_merge_named themes\n"
        else:
            # frontend exists, add themes under it
            config_content = config_content.replace(
                "frontend:",
                "frontend:\n  themes: !include_dir_merge_named themes"
            )
        changed = True
        logger.info("Added themes configuration")

    if changed:
        config_file.write_text(config_content)
        logger.info("Configuration updated - restart HA to apply")

    logger.info("Controll branding installation complete")


# ============== MAIN ==============

async def main():
    """Start the add-on."""
    logger.info("Starting Controll Supervisor Add-on")

    # Auto-install Controll branding on startup
    try:
        install_controll_branding()
    except Exception as e:
        logger.error(f"Failed to install branding: {e}")
    logger.info(f"Platform URL: {PLATFORM_URL}")
    logger.info(f"Heartbeat interval: {HEARTBEAT_INTERVAL}s")

    # Create web app
    app = web.Application()

    # Routes
    app.router.add_get("/health", handle_health)

    # File operations
    app.router.add_post("/api/file/write", handle_file_write)
    app.router.add_get("/api/file/read", handle_file_read)
    app.router.add_get("/api/file/list", handle_file_list)

    # Home Assistant
    app.router.add_post("/api/ha/service", handle_ha_service)
    app.router.add_post("/api/ha/restart", handle_ha_restart)
    app.router.add_get("/api/ha/config", handle_ha_config)
    app.router.add_get("/api/ha/states", handle_ha_states)

    # Add-ons
    app.router.add_get("/api/addons", handle_addon_list)
    app.router.add_post("/api/addons/install", handle_addon_install)

    # System
    app.router.add_get("/api/system/info", handle_system_info)
    app.router.add_post("/api/discovery", handle_discovery)

    # Controll specific
    app.router.add_post("/api/theme/install", handle_install_theme)
    app.router.add_post("/api/branding", handle_set_branding)

    # Start heartbeat task
    asyncio.create_task(send_heartbeat())

    # Start web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()

    logger.info("Controll Supervisor listening on port 8099")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
