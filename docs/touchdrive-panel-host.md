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

Verification on the Windows host: four automated tests passed (cross-platform XML, source/file restrictions, authentication forwarding, origin and body limits). Live relay verification rejected an unauthenticated command, authenticated an existing admin session, returned all three simulated cameras, and logged that test session out. TD-to-Windows access is still pending the administrator firewall prompt.
