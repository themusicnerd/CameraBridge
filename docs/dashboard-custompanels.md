# Native DashBoard CustomPanels

Files: `SW-Panasonic-Camera-Control.grid` and `SW-Marshall-Camera-Control.grid`. Both are native OGLML documents containing `abs`, `meta`, `params`, `timer`, `timertask`, `api`, `button`, `label` and `ogscript` elements. No browser widget is used. `dashboard/build_panels.py` reproducibly generates them.

API references: Ross [DashBoard documentation](https://www.rossvideo.com/support/product-documentation/dashboard/) and [CustomPanel Development Guide v10](https://documentation.rossvideo.com/files/Manuals/Enterprise%20Management/Dashboard/DashBoard%20CustomPanel%20Development%20Guide%20v10.pdf), especially parameter constraints, numeric widgets, `asyncPost`, `params.setValue`, `params.setAccess`, `ogscript.rename`, timers and mouse events. These APIs have earlier-version documentation as well; the actual local installation is 9.15.2 and remains the runtime compatibility target to verify.

Panel networking sends URL-encoded JSON using asynchronous HTTP, avoiding browser-only WebSockets and custom-header assumptions. The backend accepts this format alongside REST JSON. Tokens live in script memory. Responses never contain passwords.

Every paint control has a draft slider/numeric entry and a separate confirmed-value/state/age line. Backend feedback updates are guarded to avoid issuing writes when the UI is updated. A 200ms timer coalesces edits, sending at most one parameter per tick; the per-camera transport imposes its own interval. Polling is once per second at the panel, against central cached state rather than direct cameras.

Unknown or mode-inapplicable parameters are read-only. Communication failures and feedback age are visible. Camera change clears draft writes, invalidates local motion callbacks and sends stop to the previous camera. Closing attempts stop; the backend watchdog is the fallback when a panel crashes.

The Panasonic UI has 20 preset buttons and a one-shot overwrite confirmation. PTZ button press requests one bounded jog and release/mouse-exit requests stop; holding a button does not renew forever. This deliberately limits a lost-release event. Long continuous positioner integration is separate and pending.

## Acceptance checklist

1. Open each file in installed DashBoard; inspect the debug pane for XML and script errors.
2. Confirm cached simulator feedback appears without login in local LAB mode.
3. Create an account with the CLI and sign in to each panel; wrong credentials must not enable writes.
4. Verify Panasonic next-camera selects independent state and stops the old camera.
5. Change red gain and confirm the state line changes pending → confirmed, with matching emulator readback.
6. Select ATW; red/blue manual writes must be disabled/rejected. Select bank A/B and verify re-enable.
7. Jog all directions/zoom/focus; inspect emulator axes; release, close the panel and simulate loss to verify neutral commands.
8. Verify preset storage needs OVERWRITE and reverts to recall after use.
9. Marshall OSD/paint must remain clearly marked LAB; fixed-camera UI must show no mechanical pan/tilt.
10. Check touch hit targets, clipping and actual TD1C screen scaling; adjust panel dimensions if needed.

XML/contract tests pass. `node tests/panel_smoke.cjs` also parses every generated handler and exercises the generated API against the live local backend with a strict parameter/label test adapter. This is a V8 contract test, not the DashBoard Rhino engine.

Native application validation subsequently confirmed both panels load and process recurring feedback in DashBoard9.15.2. A temporary loopback HTTP observer forwarded requests to the existing backend, and instrumented panel copies emitted success only after the normal parameter/label update path returned. No production equipment or credentials were involved. See `native-dashboard-validation.md`. Visual layout/touch interaction still cannot be claimed because screen capture fails. Authenticated UI control tests are pending local account provisioning.
