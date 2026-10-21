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

Both remain inside the shared backend/state manager. The server rejects non-loopback binds and physical camera targets. Do not enter these localhost endpoints as a Carbonite LAN device and expect connectivity. A future trusted-LAN hardware acceptance listener is separate work.

For intentional lab preset-store tests, add `--visca-allow-store` to the service. Without it, raw controller preset stores are rejected. Native panel preset stores retain their own OVERWRITE confirmation. The current development validation run explicitly enabled simulator stores.

## Implemented subset and safety

- Address1, FF-terminated frames, maximum 16 bytes, TCP fragmentation and concatenation handling.
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
