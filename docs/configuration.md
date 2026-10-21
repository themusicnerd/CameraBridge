# Configuration reference

The application reads a JSON file at startup.
For desktop use, select the camera configuration in the [control panel](desktop.md).
The panel saves its own copy with the selected HTTP settings.
It does not change the external configuration file.
Use `--config PATH` to select it.
The default file is `config.example.json` in the application resources.
Copy the example to a user-owned location before you change it.

| Field | Meaning and limits |
|---|---|
| `bind` | Explicit IPv4 or IPv6 address; HTTPServer currently requires a usable IPv4 bind |
| `port` | HTTP port; 1024 through 65535; default 8088 |
| `poll_seconds` | Delay between completed camera query rounds; 1 through 60 |
| `trusted_hosts` | CIDR list for clients that can reach the HTTP API |
| `ross` | Bench address record; this object does not start a gateway |
| `cameras` | List of configured cameras |

Use an IPv4 bind for this release.
Lab mode requires a loopback bind and enabled simulator camera entries.
Disabled hardware entries can remain in a lab configuration.
The desktop changes out of lab mode when an enabled physical camera is applied.
Keep simulator HTTP ports on loopback.

## Camera fields

| Field | Meaning |
|---|---|
| `number` | Unique camera number from 1 through 255; determines the PIVOTCam port |
| `pivotcam` | True enables this camera when the global PIVOTCam service is enabled |
| `allow_store` | True permits remote shot overwrite; default false |
| `id` | Unique ASCII camera ID; letters, digits and underscores |
| `name` | Operator camera name |
| `manufacturer` | `Panasonic` or `Marshall`; must match the driver |
| `model` | `AW-HE130` for the Panasonic driver |
| `driver` | `panasonic` or `marshall-lab` |
| `host` | Panasonic address or hostname without a URL scheme or credentials |
| `port` | Panasonic HTTP port; 1 through 65535 |
| `carbonite_input` | Displayed switcher input association |
| `simulator` | True for a simulator; required for `marshall-lab` |
| `enabled` | False excludes a camera from the state engine |

Marshall `address` and `gateway` values are lab information in this release.
They do not enable a production serial driver.
Do not include passwords, tokens or credential fields in a configuration file.

## Prepare a physical Panasonic test

1. Copy `config.example.json` to a separate file.
2. Keep only the required AW-HE130 camera entry.
3. Set its real address and HTTP port.
4. Set `simulator` to false.
5. Keep the HTTP service on loopback for the first test.
6. Start with `--config PATH --ensure-admin`, without `--lab` or `--visca-lab`.
7. Check feedback before you send a movement command.

This procedure does not enable the Carbonite relay for a physical camera.
That relay permits simulator targets only.
Use the separate numbered PIVOTCam service for an explicit physical Panasonic target.
Read [camera setup](camera-setup.md) before you enable it.
An authenticated-camera protocol is not implemented.

## Apply a saved configuration

1. Load or import JSON on the web Configuration page.
2. Select **Validate and save**.
3. Check the validation result.
4. Stop the service.
5. Back up the active configuration.
6. Restart with `--config DATA/config.pending.json`.

Replace DATA with the selected data directory.
Restart does not restore session tokens or queued motion.
