# HTTP API reference

The default service URL is `http://127.0.0.1:8088`.
All write requests require a login token, except the login request itself.
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
| GET | `/health` | Service name and LAB or hardware mode |
| POST | `/api/login` | Create a session |
| POST | `/api/logout` | End the supplied session |
| GET or POST | `/api/state` | Camera state and events; loopback LAB reads can omit login |
| POST | `/api/command` | Authenticated camera command |
| GET | `/api/config` | Administrator; current configuration |
| POST | `/api/config` | Administrator; validate and save pending configuration |
| GET | `/api/snapshots` | Saved paint snapshots |
| POST | `/api/snapshot` | Capture confirmed paint values |
| POST | `/api/lab/ross/bus` | Administrator; enabled VISCA lab only |
| POST | `/api/service/stop` | Administrator; LAB service only |

The TouchDrive host does not expose `/api/service/stop`.
It permits only its fixed path list.

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
