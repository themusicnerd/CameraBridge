# Feature and acceptance matrix

Status meanings: **tested** = exercised by local automated tests, **hardware pending** = software exists but physical behaviour has not been measured, **blocked** = required facts or access missing, **pending** = not yet implemented, **unsupported** = not applicable.

| Feature | Software status | Physical/platform status |
|---|---|---|
| AW-HE130 HTTP transport, escaped CGI commands | Tested | Hardware pending |
| Pan/tilt directions, simultaneous axes, zoom/focus, stop | Tested against CGI emulator | Hardware pending |
| AW-HE130 iris/focus modes and positions, zoom position | Implemented; protocol validation tests | Hardware pending |
| AW-HE130 red/blue gain, WB mode, detail | Tested readback, including WB wire/query mapping | Hardware pending |
| Remaining Panasonic paint, AWB execution, notifications | Pending | No hardware available |
| HE40/HE120 model-specific profiles | Pending; configuration rejects these profiles | Hardware pending |
| Panasonic preset recall/store, overwrite guard | Tested | Hardware pending; activity remains unverified |
| Central confirmed/pending/stale/error state | Tested | Hardware pending |
| Ownership, stale generation rejection, motion watchdog | Tested | Network failure cannot guarantee physical stop |
| Separate Panasonic native .grid | Aura redesign; XML/geometry/contract tested; native feedback callback verified | DashBoard 9.15.2; visual/touch/authenticated control tests pending |
| Separate Marshall native .grid | Aura redesign; XML/geometry/contract tested; native feedback callback verified | DashBoard 9.15.2; visual/touch/authenticated control tests pending |
| Manufacturer logos, persistent preset names | Implemented; native logo URLs and name persistence tested | Regenerate URLs after relocating source |
| Marshall paint/OSD lab model | Implemented; synthetic state | Not camera wire emulation |
| Marshall RS485 TCP serialization/turnaround | Implemented | Gateway hardware and command map pending |
| CV226/CV228 direct serial command/readback map | Blocked | Need exact-model protocol or verified captures |
| Unknown third Marshall model | Blocked | Need model and firmware |
| Mechanical PTZ for fixed Marshall | Unsupported | Intentionally absent |
| Administration status/configuration/events | Implemented; API tests | Local HTTP service running |
| Auth, operator/admin roles, trusted hosts, CSRF origin checks | Tested | Credential provisioning required by operator |
| Snapshot capture, persistent JSON, exclude unknown values | Tested | Recall/matching/import/compare pending |
| Configuration validation/export/import through admin | Implemented; pending config saved | Applying requires explicit restart |
| WebSocket push | Pending | Polling currently used |
| TCP receive-only protocol capture | Implemented | No Ross capture yet |
| Serial VISCA/TCP → Panasonic bridge | Implemented and tested against lab emulators, including preset store/recall | LAN/physical targets rejected; real Ross initialization and timing pending |
| Native Carbonite Camera Custom Controls | Current manufacturer event/configuration references documented | Actual Recall/Fast/Store/Halt tests pending |
| Preset-only selection and safe handover | Implemented and tested with explicit simulator bus events; Program ignored | No real bus/delegation adapter or physical positioner test yet |
| TouchDrive three hardware knobs | Research pending | No hardware device access attempted |
| TD1C read-only host diagnostic | Implemented | SSH authentication unavailable |
| TD1C persistent service/support/update survival | Blocked | Needs host report and Ross confirmation |
| Linux user service unit/rollback instructions | Supplied | Not installed or Linux-tested |
| Self-contained executable/resource benchmarks | Pending | Python source runtime used on Windows |
| Production acceptance, normal-switching impact | Pending | No production readiness claim |

## Test evidence

`python -m unittest discover -v`: 27 tests passed in 42.877 seconds; the complete run is recorded in `test-results.txt`. It covers account provisioning, authentication, CGI readback, watchdog/ownership, Aura layout geometry, raw serial-VISCA/TCP, Preset-only selection and handover, disconnect/service-close stopping, and preset storage protection. Tests use emulators, not physical cameras. There are no manufacturer hardware captures in the fixtures directory; the Panasonic fixture is explicitly labelled manufacturer-documented examples.

`node tests/panel_smoke.cjs`: the redesigned Panasonic's 98 handlers and Marshall's 55 handlers parse in V8, and each generated panel API retrieves live lab state and updates its expected parameter/label/style IDs. It does not by itself establish Rhino or native rendering compatibility. See `test-results.txt` for the final test run.

Later native application validation: both panels loaded in DashBoard9.15.2. Instrumented copies emitted recurring feedback-success callbacks after executing the native parameter/label update path. This adds native ogScript/runtime evidence beyond the V8 test. Screenshot capture, visual layout, touch operation and authenticated control remain pending. See `native-dashboard-validation.md`.

The Aura redesign subsequently passed the same native callback check. `tools/visca_lab_demo.py --store` also passed against the running service with simulator remote stores explicitly enabled. This checks the real local TCP/HTTP chain, not the physical Ross controller.

## Network discovery evidence

One bounded TCP connect check per endpoint/port, 21 October 2026:

| Host | Open TCP ports observed | Other checks |
|---|---|---|
| TD1C 192.168.96.122 | 22, 5900, 5253 | HTTP 80/443 did not connect; FTP21/SFTP2222 probes did not produce a banner within one second |
| Carbonite 192.168.96.123 | 22, 80, 5253 | 443/5900 did not connect |

An open port is not an authenticated session or a complete service identification. `ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@192.168.96.122 uname -a` was refused with `Permission denied (publickey,password)`. No password guessing was performed. No commands executed on the TD1C.
