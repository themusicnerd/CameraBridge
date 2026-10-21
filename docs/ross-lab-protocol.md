# Ross integration lab

## Documented basis

The current [Ross PTZ Camera Control Plugin manual for DashBoard 9.15+](https://help.rossvideo.com/cms/supported-products/pdf/User_Manual_for_PTZ_Camera_Control_Plugin.pdf), VISCA Gateway section, identifies serial VISCA over TCP. This differs from assuming Sony's UDP VISCA-over-IP wrapper and sequence header. The manual also says the modern gateway is not compatible with the legacy PIVOTCam Control Panel; compatibility must be assessed against the installed driver/plugin combination.

The incoming command syntax implemented here is a small subset of [Sony's VISCA Command List, E-042-100-13, software 2.10](https://pro.sony/support/res/manuals/E042/3230148ee903c204b912cca5c2c3f5aa/E0421001M.pdf). It is a controller-side protocol reference; it is not a Marshall CV226/CV228 serial profile. The actual Carbonite/PIVOTCam command sequence, initialization and timing have not yet been captured.

## Start

```sh
python -m backend.server --lab --visca-lab
```

The default example cameras create loopback listeners:

| Listener | Target |
|---|---|
| 127.0.0.1:19010 | pana1 CGI emulator |
| 127.0.0.1:19011 | pana2 CGI emulator |

Both remain inside the shared backend/state manager. The server rejects non-loopback binds and physical camera targets. Do not enter these localhost endpoints as a Carbonite LAN device and expect connectivity. The separate frame-restricted LAN development relay described below is available for simulator testing.

For intentional lab preset-store tests, add `--visca-allow-store` to the service. Without it, raw controller preset stores are rejected. Native panel preset stores retain their own OVERWRITE confirmation. The current development validation run explicitly enabled simulator stores.

## Implemented subset and safety

- Address1, FF-terminated frames, maximum 16 bytes, TCP fragmentation and concatenation handling.
- Sony serial VISCA AddressSet broadcast (88 30 01 FF -> 88 30 02 FF) for one virtual camera, plus broadcast/addressed IF_Clear. Interface clear stops motion. These replies follow Sony E0421001M, pages 6-7.
- Variable pan/tilt, standard/variable zoom and focus, focus auto/manual and focus-mode inquiry.
- Preset recall/store with zero-based wire number mapped to operator shot 1..100.
- ACK/completion/error framing for this lab subset. Preset completion is immediate because the emulator applies a preset synchronously. It is **not** a valid physical completion implementation.
- One active TCP controller per camera endpoint; bounded queues; coalesced movement;300 ms stale-receive rejection.
- Shared ownership/locks and900 ms motion watchdog. Pan/tilt and zoom states coexist, so a zoom update does not erase pan/tilt.
- Drop/disconnect and service-close stop attempts. No automatic motion replay.

Speed mapping preserves the lowest and highest supported values across the two protocols. Its curve is a software normalization, not a measured optical-speed calibration. Physical inversion, deadbands and response curves remain acceptance items.

## Preset-only following

Authenticated administrator POST `/api/lab/ross/bus` accepts an explicit simulator event `{bus: "preset"|"program", camera: "pana1"|"pana2"}`. It is available only when the lab gateway is enabled. The Panasonic panel's TD1C page exposes the same labelled simulator input.

A Preset event stops the previous target before changing selection, increments the selection epoch, clears motion and requires fresh pan/tilt and zoom neutral input before movement. Program events do not change the target. A packet for the wrong target or an older epoch is rejected. A watchdog/external stop also requires neutral input before resuming.

These events are **not** obtained from Carbonite yet. The service does not infer Program/Preset bus events from camera commands or tell the UI that a simulated selection is actual TD1C delegation.

## Repeatable controller demonstration

```sh
python tools/visca_lab_demo.py
# With intentional store enabled on the service:
python tools/visca_lab_demo.py --store
```

Enter the CameraBridge account password interactively. The tool authenticates selection through the API, then sends raw TCP controller frames. It checks pan/tilt plus zoom, Program-only non-retargeting, old-camera stop, stale-target rejection and preset 20 recall/store. No credentials are embedded in the tool or logged.

The live local demonstration passed on 21 October 2026. Regression tests also cover fragmented frames, focus inquiry, store rejection, persistent names, wrong-target/hardware rejection and neutral handover. This is software/simulator evidence, not a test of the TD1C positioner or Carbonite Custom Controls.


## Carbonite LAN development test, 21 October 2026

A separate `tools/ross_dev_relay.py` now exposes a simulator-only test endpoint:

```powershell
python tools/ross_dev_relay.py --bind 192.168.96.61 --frame 192.168.96.123 --port 19010 --output runtime/ross-carbonite-pana1.jsonl
```

The loopback backend/gateway restrictions remain in place. This relay accepts only the specified frame IP, one active controller, validates the target is a loopback Panasonic emulator in LAB mode before connection, and logs both directions with a 2 MB capture limit. Non-VISCA initial framing is captured and disconnected without forwarding or fabricated responses. Seven focused tests cover framing rejection, duplex fragmentation, peer rejection, target guards, capture limit and disconnect/shutdown cleanup.

The user's original slot 0 Beauty device used Cambot_1.0 and emitted STX `000 NC` ETX (`02 30 30 30 20 4e 43 03`). Changing the driver and saving did not replace the old session. CameraBridge recreated only this test slot as PIVOTCam_1.1 and restored Input 1 -> Beauty-S0, channel 1, inversion No. Carbonite then sent AddressSet `88 30 01 FF`; the implemented reply `88 30 02 FF` allowed it to advance to periodic VISCA inquiries. Focus-mode inquiry `81 09 04 38 FF` receives simulator state `90 50 03 FF` (manual). Additional observed paint inquiries (35, 39, 4A, 4B, 4C) are unsupported and receive syntax error `90 60 02 FF`; no paint feedback is fabricated. See `ross-carbonite-first-capture.json`. Positioner motion, actual Preset-bus following and native camera CC remain unverified.

Panasonic 1 has been selected explicitly as the fixed lab target for this first-device test. That is a test fixture, not inferred switcher bus state. The existing neutral interlock still requires both pan/tilt and zoom stop commands after handover or a fault before accepting motion. The watchdog remains 900 ms. Raw preset stores follow the underlying lab server's explicit store flag (enabled in this development run); use recall/movement only for the initial controller check.

An additional Windows firewall rule, if approved, is named `CameraBridge Carbonite simulator test`, scoped to remote192.168.96.123, local192.168.96.61, TCP19010. The connection succeeded before this additional rule was confirmed. Rollback: stop the relay and, if present, remove only that rule with `netsh advfirewall firewall delete rule name="CameraBridge Carbonite simulator test"`. The TD panel host uses a separate TCP8089 rule.


The backend was restarted to load initialization support; simulator positions and in-memory presets reset. Both native panel sessions were signed in again. No physical camera was attached. The primary initialization specification is [Sony E0421001M](https://pro.sony/support/res/manuals/E042/3230148ee903c204b912cca5c2c3f5aa/E0421001M.pdf), pages 6-7.

## First physical positioner test

The operator moved/released pan, tilt and zoom and reported push/pull at the end. Actual frame capture and central motion events now verify the TouchDrive -> Carbonite -> CameraBridge -> Panasonic emulator path for positive/negative pan, tilt and zoom, including neutral stop commands. The camera ended `moving=false` with the neutral interlock ready. The retained event window contains 51 accepted pan/tilt and 20 accepted zoom commands; it also contains a watchdog stop. Some commands returned `90 60 41 FF` (command not executable); the current implementation does not log the rejection reason, so stale timing, neutral and ownership checks cannot yet be distinguished from this capture. This is a partial movement pass, not smooth continuous-motion acceptance. No separate focus, focus-mode or other push/pull command was observed. See `ross-positioner-first-test.json` for raw window and retained accepted motion events. Presets, native Custom Controls, physical-camera movement and real bus following remain unverified.
