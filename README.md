# CameraBridge

Native Ross DashBoard camera panels, a shared Python backend, and a Windows/Linux camera-control lab.

**Development release 0.1 — 21 October 2026. Not production accepted.**

The two native DashBoard panels are deployed on the development TouchDrive. The backend and camera emulators run on Windows. Carbonite slot 0 Beauty uses PIVOTCam_1.1 at the simulator relay, with Input 1 / channel 1 restored. Positioner motion, shot store/recall and an operator-triggered Custom Control recall have reached the simulator. Continuous motion, actual bus following and physical-camera completion remain acceptance items.

## Start the lab

Requires Python 3.11 or newer, with no third-party Python dependencies. From this directory:

```powershell
python -m backend.server --init-user admin
python -m backend.server --lab --visca-lab
```

The first command prompts for a password and stores only a salted PBKDF2 hash. Run it while the service is running if an account has not yet been created. Non-empty passwords are accepted; there is no minimum length requirement. An additional operator account can be created with `--init-user operator --role operator`.

Open <http://127.0.0.1:8088>. The service starts two independent Panasonic CGI emulators (18080 and 18081), an explicitly synthetic Marshall lab model, and optional lab serial-VISCA/TCP endpoints (19010 and 19011). Check those ports are free first. All lab listeners bind to loopback.

In **DashBoard → File → Open**, open:

- `dashboard/SW-Panasonic-Camera-Control.grid`
- `dashboard/SW-Marshall-Camera-Control.grid`

Use the same CameraBridge login in each panel. The URL defaults to `http://127.0.0.1:8088`. The panels use native OGLML controls and ogScript `asyncPost`; they do not embed a browser. Password entries clear after sign-in; sessions are held in memory. Do not save a panel containing a typed password.

The panels follow the flat Aura reference with manufacturer logos and larger native fader handles. Navigation targets are 104×56; command buttons and entries are at least 48 pixels high. Marshall Paint and Image each hold four faders. The 1366×800 canvas fits inside the TD's 1920×1080 DashBoard desktop with its tree and tabs visible. Login is on Config. Enable touch control on PTZ before jogging. Persistent shot names are edited on Presets. Regenerate with `python dashboard/build_panels.py` after moving the project so local logo URLs resolve on the new host. See [touch layout verification](docs/touch-layout-validation.md).

To stop the lab, press Ctrl+C in its terminal. Stop controls and the watchdog cannot guarantee a physical camera stops if its network is broken; see the safety limitations.

## Implemented scope

The AW-HE130 driver implements variable pan/tilt, zoom/focus speed, neutral stop, physical presets 1–100, iris mode/position, focus mode/position, zoom position, red/blue gain, white-balance modes and detail. Supported paint values are queried independently after writes. Additional paint families and HE40/HE120 profiles remain pending.

Marshall paint/OSD controls currently operate **only the lab model**. The RS485 TCP transport and bus mutex exist, but CV226/CV228 direct command bytes are deliberately blocked until an exact-model command list or annotated captures establish them.

Modern Ross gateway transport is documented as serial VISCA over TCP. A **lab-only** bridge translates a tested subset to the Panasonic CGI emulators. Its core listener rejects LAN binds and physical targets; a separate IP-restricted development relay accepts the Carbonite. Actual frame capture verifies initialization, variable motion and shot commands through the simulator, including an operator-triggered Custom Control recall. Explicit simulator Preset events select a target; these are not actual switcher bus feedback. Handover stops the old camera and requires fresh neutral input. See `docs/ross-lab-protocol.md` and `docs/ross-hardware-acceptance.md` for partial passes and remaining work.

Run `python tools/visca_lab_demo.py` for the controller demonstration. Intentional simulator remote stores require `--visca-allow-store` on the service and `--store` on the demo. Store is otherwise blocked at the raw gateway.

## Verify

```powershell
python -m unittest discover -v
python dashboard/build_panels.py
python tools/host_diagnostic.py --output host-report.json
```

See `docs/feature-matrix.md` for implementation and hardware-validation status, `docs/dashboard-custompanels.md` for panel acceptance, and `docs/installation.md` for deployment and rollback.

Both redesigned Aura panels load in local DashBoard 9.15.2. Instrumented copies confirmed recurring native timer requests and successful feedback callbacks after updating native parameter/label values. The development admin account is provisioned and live backend login is verified. Visual layout, touch operation and authenticated native controls remain pending because the Windows screenshot helper times out. See `docs/native-dashboard-validation.md` and `docs/aura-design.md` for the evidence and its limits.

Native panels on the connected TouchDrive with the Windows development backend: see [TouchDrive panel hosting](docs/touchdrive-panel-host.md).
