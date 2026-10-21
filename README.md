# CameraBridge

Native Ross DashBoard camera panels, a shared Python backend, and a Windows/Linux camera-control lab.

**Development release 0.1 — 21 October 2026. Not production accepted.**

The current development focus is the two separate native DashBoard panels and local camera emulation, as requested. No software has been installed on the TD1C and no switcher configuration has been changed.

## Start the lab

Requires Python 3.11 or newer, with no third-party Python dependencies. From this directory:

```powershell
python -m backend.server --init-user admin
python -m backend.server --lab
```

The first command prompts for a password and stores only a salted PBKDF2 hash. Run it while the service is running if an account has not yet been created. Passwords must be at least 12 characters. An additional operator account can be created with `--init-user operator --role operator`.

Open <http://127.0.0.1:8088>. The service starts two independent Panasonic CGI emulators (18080 and 18081) plus an explicitly synthetic Marshall lab model. Check those ports are free first. All lab listeners bind to loopback.

In **DashBoard → File → Open**, open:

- `dashboard/SW-Panasonic-Camera-Control.grid`
- `dashboard/SW-Marshall-Camera-Control.grid`

Use the same CameraBridge login in each panel. The URL defaults to `http://127.0.0.1:8088`. The panels use native OGLML controls and ogScript `asyncPost`; they do not embed a browser. Password entries clear after sign-in; sessions are held in memory. Do not save a panel containing a typed password.

To stop the lab, press Ctrl+C in its terminal. Stop controls and the watchdog cannot guarantee a physical camera stops if its network is broken; see the safety limitations.

## Implemented scope

The AW-HE130 driver implements variable pan/tilt, zoom/focus speed, neutral stop, physical presets 1–100, iris mode/position, focus mode/position, zoom position, red/blue gain, white-balance modes and detail. Supported paint values are queried independently after writes. Additional paint families and HE40/HE120 profiles remain pending.

Marshall paint/OSD controls currently operate **only the lab model**. The RS485 TCP transport and bus mutex exist, but CV226/CV228 direct command bytes are deliberately blocked until an exact-model command list or annotated captures establish them.

Carbonite/PIVOTCam framing and Preset-bus following are **not verified or enabled**. The receive-only TCP capture tool is supplied to investigate them without fabricating switcher events.

## Verify

```powershell
python -m unittest discover -v
python dashboard/build_panels.py
python tools/host_diagnostic.py --output host-report.json
```

See `docs/feature-matrix.md` for implementation and hardware-validation status, `docs/dashboard-custompanels.md` for panel acceptance, and `docs/installation.md` for deployment and rollback.

Both panels load in local DashBoard 9.15.2. Instrumented copies confirmed recurring native timer requests and successful feedback callbacks after updating native parameter/label values. Visual layout, touch operation and authenticated controls remain pending: the Windows screenshot helper times out, and the local admin password has not yet been provisioned. See `docs/native-dashboard-validation.md` for the evidence and its limits.
