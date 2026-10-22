# HTTP API reference

The default service URL is `http://127.0.0.1:8088`.
Write requests require a login token when authentication is enabled.
Authentication defaults to enabled.
Set `authentication_enabled` to false to allow trusted hosts to use the service without sign-in.
Trusted host checks apply before API processing.

## Authentication

Send JSON with `Content-Type: application/json`.
Use `Authorization: Bearer TOKEN` for authenticated requests.
A JSON `token` field is also accepted for native panel requests.
Do not put a token in a URL.

```json
{"username":"admin","password":"YOUR_PASSWORD"}
```

POST this object to `/api/login`.
The response contains `token` and `role`.
Native panels can send URL-encoded `request=JSON` through ogScript.

## Endpoints

| Method | Path | Access and result |
|---|---|---|
| GET | `/` | Web interface |
| GET | `/health` | Service mode, authentication option, and reconfiguration state |
| GET | `/api/session` | Current role and authentication option |
| GET | `/help` | Setup procedures |
| POST | `/api/login` | Create a session |
| POST | `/api/logout` | End the supplied session |
| GET or POST | `/api/state` | Camera state and events; loopback LAB reads can omit login |
| POST | `/api/command` | Authenticated camera command |
| GET | `/api/config` | Administrator; current configuration |
| POST | `/api/config` | Administrator; validate and save pending configuration |
| POST | `/api/setup` | Administrator; revision-checked native camera and bridge setup |
| POST | `/api/sony/fingerprint` | Administrator; read a camera SSH fingerprint |
| POST | `/api/sony/credentials` | Administrator; save camera access separately from configuration |
| GET | `/api/snapshots` | Saved paint snapshots |
| POST | `/api/snapshot` | Capture confirmed paint values |
| POST | `/api/lab/ross/bus` | Administrator; enabled VISCA lab only |
| POST | `/api/service/stop` | Administrator; LAB service only |

The TouchDrive host does not expose `/api/service/stop`.
It permits only its fixed path list.

## Native camera setup

Send `operation: "load"` to `/api/setup`.
The response contains `configuration`, `revision`, and `pending`.
It returns the saved pending configuration if one exists.
Other operations must include that revision.
An older revision returns HTTP 400 without changing the saved setup.

| Operation | Required fields |
|---|---|
| `autosave` | Complete `configuration`; save and apply while retaining HTTP sessions |
| `save` | Complete `camera` object; `previous` is its existing ID, or empty for a new camera |
| `remove` | `camera` ID and `confirmation: "REMOVE"` |
| `bridge` | Complete `pivotcam` and `tally` objects |
| `apply` | No additional fields |

Each response includes the updated configuration and revision.
Saving does not change the running engine.
Apply requests the existing desktop restart procedure when desktop control is available.
A console service reports that a manual restart is required.
See [configuration](configuration.md) for camera fields.

The Sony access endpoint accepts a camera in the active or saved pending configuration.
Supply its `camera` ID, `username`, `password`, verified `fingerprint`, and `acknowledge_terms: true`.
The response contains status only.
The setup and configuration endpoints never return the stored camera password.

## Camera commands

Supply `camera`, `action` and a `data` object.
Ownership comes from the session token, not a client owner field.

| Action | Data |
|---|---|
| `claim` | Empty object; response contains movement generation |
| `stop` | Empty object; attempts neutral commands |
| `write` | `parameter` and integer `value` |
| `move` | `generation`, plus `pan`, `tilt`, `zoom` and `focus`; each −49 through 49 |
| `preset` | `number` 1 through 100; `store`; `confirm` must equal `OVERWRITE` for store |
| `label_preset` | `number` and `name`; name length 1 through 80 |
| `lock` | Administrator; boolean `value` |
| `osd` | Marshall lab; `key`: menu, up, down, left, right, enter or back |

Example:

```json
{"camera":"pana1","action":"write","data":{"parameter":"iris","value":1400}}
```

A queued response does not confirm the camera value.
Read `/api/state` until the independent query confirms it.
Preset state remains `last command sent, unverified`.

For a snapshot, supply `camera`, `name` and optional `notes`.
For configuration, supply a `configuration` object.
Set `apply` to true to request a restart from the desktop supervisor.
The console service saves the file and reports that an explicit restart is required.
For a lab bus event, supply `bus` and `camera`.
Bus values are `preset` or `program`.
These events do not change the real switcher.

## Errors and limits

| Status | Meaning |
|---|---|
| 400 | Invalid body, field or value |
| 401 | Authentication required on a direct read |
| 403 | Host, session, role or origin denied |
| 404 | Path or operation is unavailable |
| 502 | Device or upstream request failed |

Bodies have a 65536-byte limit.
The backend permits 24 HTTP request threads.
The TouchDrive host permits eight request threads and bounded upstream responses.
See [security](security.md) for session and network limits.

## Persistent Browser Sessions

The login response contains a random session token.
The browser stores it locally for this CameraBridge origin.
The server stores its hash in the credentials database.
Sign-out or a password change revokes the session.
Open-access tokens issued while authentication is disabled are revoked when authentication is enabled again.

## TSL State

The state response includes `tsl` with enabled, listening, source, bind, port, packet counts, and last-packet age.
Its `state` is disabled, not listening, waiting, receiving, or stale.
Each camera tally object separates `received`, `requested`, `actual`, and readback status.


## Preset Recall Speed

Each camera state contains `preset_speeds`, keyed by shot number.
Use `label_preset` with `number`, `name`, and `speed` to save metadata.
This operation does not store a camera position.
The `preset` action accepts `speed` from 1 to 30.
A store saves this speed after the camera accepts the store command.
A recall uses the saved speed if the request has no override.
An override applies to that recall and does not replace the saved value.
Carbonite and custom-control recalls also use the saved value.
The driver sets and queries the camera speed before it sends the recall.
A failed speed check prevents that recall.
Supported speed profiles are HE40, HE42, UE70, HE50, HE60, HE120, and HE130 families.

## White Balance and Movement

Use `write` with `wb_mode` for ATW or a manual memory.
Use `white_balance_once` after the selected manual memory is confirmed.
The `white_balance_once` state separates command delivery from completion.
Camera completion notifications are not received in this release.
HE40-family gain commands use QGR, QGB, ORG, and OBG.
The public gain range stays 0 to 300, with 150 as zero.
These camera families use steps of 5 in that range.
The panel displays each native step as one gain step.

Dashboard button release uses `stop` with `active_only` set to true.
Unknown axis states are always stopped.
The Stop button and watchdog still send all supported axis stops.
