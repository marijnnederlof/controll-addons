# Controll Add-ons for Home Assistant

Add-on repository for Controll fleet management platform.

## Add-ons

### Controll Supervisor

Remote management add-on that enables:
- File operations (themes, dashboards, configurations)
- Service calls to Home Assistant
- Add-on management
- Network discovery for domotica systems
- Heartbeat to Controll platform

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the three dots menu → **Repositories**
3. Add: `https://github.com/wooniot/controll-addons`
4. Find "Controll Supervisor" and install

## Configuration

```yaml
hub_token: "your-hub-token-from-controll-portal"
platform_url: "https://api.controll.it"
heartbeat_interval: 300
log_level: "info"
```

## API Endpoints

The add-on exposes a local API on port 8099:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/file/write` | POST | Write file to config |
| `/api/file/read` | GET | Read file from config |
| `/api/file/list` | GET | List files in directory |
| `/api/ha/service` | POST | Call HA service |
| `/api/ha/restart` | POST | Restart Home Assistant |
| `/api/ha/config` | GET | Get HA config |
| `/api/ha/states` | GET | Get all entity states |
| `/api/addons` | GET | List installed add-ons |
| `/api/addons/install` | POST | Install add-on |
| `/api/system/info` | GET | Get system info |
| `/api/discovery` | POST | Scan for domotica systems |
| `/api/theme/install` | POST | Install theme |
| `/api/branding` | POST | Set HA branding |

All endpoints (except `/health`) require `Authorization: Bearer <hub_token>` header.

## Security

- The add-on only accepts requests with valid hub token
- File operations are restricted to `/config` directory
- No shell access exposed externally
- Communication with Controll platform uses HTTPS
