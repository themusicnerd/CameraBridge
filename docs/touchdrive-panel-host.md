# TouchDrive development panel hosting

The Windows PC runs the backend, emulators, and `tools/td_panel_host.py`. The TouchDrive runs only native DashBoard `.grid` panels. No backend package, Linux service, or root login is required for this arrangement.

For this development bench:

- Windows: `192.168.96.61`, backend loopback `8088`, panel host LAN `8089`.
- TD1C: `192.168.96.122`, VNC `5900`.
- Panel downloads: `http://192.168.96.61:8089/Panasonic.grid` and `/Marshall.grid`.
- Both generated downloads use the Windows LAN backend address and HTTP manufacturer logos, replacing Windows-only file URLs. Original desktop panel files are unchanged.

Start the backend using the existing Windows lab launcher, then run from the project directory:

```powershell
python tools/td_panel_host.py --bind 192.168.96.61 --touchdrive 192.168.96.122
```

This host exposes only two panel files, two logos, health, and a fixed POST allowlist (login/logout/state/command/snapshot/explicit lab bus simulation). It accepts only the selected TD address and the Windows host itself. Commands keep the existing backend session authentication. Config and service-stop endpoints, filesystem paths, CGI emulators, and raw VISCA ports are not exposed through it. Requests log only method/path/source on first use, never bodies or tokens. The development host uses plain HTTP on this isolated bench; it is not a general production HTTPS deployment.

If Windows blocks the connection, an administrator can create this narrowly scoped rule:

```powershell
New-NetFirewallRule -DisplayName 'CameraBridge TD1C development panels' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress 192.168.96.61 -LocalPort 8089 -RemoteAddress 192.168.96.122 -Profile Any
```

Download the panels in the TD's browser, then open the downloaded files in DashBoard. Use Config to sign in to the existing CameraBridge account. Keep the Windows host and both Python processes running. Addresses must be updated deliberately if DHCP changes them. There is no automatic startup installation.

Rollback: close the new CameraBridge tabs in DashBoard; stop the panel-host process; remove only the named firewall rule if it was created:

```powershell
Remove-NetFirewallRule -DisplayName 'CameraBridge TD1C development panels'
```

Remove only the newly downloaded CameraBridge files if no longer wanted. Do not remove any Ross application directories, existing panels, or device connections. Root installation and TD backend compatibility remain separate unresolved work. Physical positioner, Carbonite Preset follow, and custom-control shot calls still require hardware acceptance described in `ross-hardware-acceptance.md`; the displayed LAB functions are simulations.

Verification on the Windows host: four automated tests passed (cross-platform XML, source/file restrictions, authentication forwarding, origin and body limits). Live relay verification rejected an unauthenticated command, authenticated an existing admin session, returned all three simulated cameras, and logged that test session out. TD-to-Windows access is verified; the administrator approved the scoped firewall rule.


## Connected TD1C acceptance, 21 October 2026

Both final files are open and authenticated in the TD DashBoard:

- `/home/touchdrive/Downloads/CameraBridge-Marshall.grid`
- `/home/touchdrive/Downloads/CameraBridge-Panasonic.grid`

The Panasonic PTZ page is visible with touch jogging disabled. The backend and emulators remain on Windows. No backend service or startup entry was installed. Existing Ross device connections remain in the TD tree.

Verified using the actual TD UI and central events:

- Both manufacturer logos and live simulator feedback.
- Existing CameraBridge admin login.
- Marshall black level: 0 to 1 to 0, confirmed readback.
- Panasonic zoom position: 1365 to 1366 to 1365, confirmed CGI emulator readback.
- Panasonic preset 20 recall: event received for pana1, store=false.

Native testing exposed two OGLML issues that were fixed before deploying these final files: onchange listeners must be registered at the panel root with explicit OIDs, and local values must be temporarily writable while applying feedback before restoring operator access. Regression checks cover the root listener mapping and read-only feedback contract. Six focused Python tests and both live-feedback script checks pass.

Earlier exploratory downloads (Marshall.grid, Marshall (1).grid, Panasonic.grid and Panasonic (1).grid) are superseded; their tabs were closed. An empty exploratory `/data/bin/carbonite/DashBoard/CameraBridge-Panasonic.grid` also exists and is not the deployed operator panel. Use the two final Downloads files above. Numeric text entry is refreshed by polling; use the verified sliders/spinners for this development build while text-entry focus handling is refined.

No physical camera was connected. Hardware joystick delegation, real Carbonite Preset follow, custom-control shot events, and physical preset completion remain unverified. The TD1C simulation page is not a hardware integration test.
