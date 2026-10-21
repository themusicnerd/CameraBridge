# TouchDrive panel host

The Windows host runs the backend and emulators.
The TouchDrive runs native grid panels and its browser.
This arrangement does not install the backend on the TouchDrive.

| Bench item | Address |
|---|---|
| Windows host | 192.168.96.61 |
| Backend | 127.0.0.1:8088 |
| Panel host | 192.168.96.61:8089 |
| TouchDrive | 192.168.96.122 |
| Carbonite frame | 192.168.96.123 |

## Start the host

1. Start the backend on the Windows host.
2. Start a second terminal in the application directory.
3. Run the panel host command.

Package command:

```powershell
.\CameraBridge.exe panel-host --bind 192.168.96.61 --touchdrive 192.168.96.122
```

Source command:

```powershell
python tools/td_panel_host.py --bind 192.168.96.61 --touchdrive 192.168.96.122
```

4. Open the panel download URL in the TouchDrive browser.
5. Download the applicable grid file.
6. Open that file in DashBoard.
7. Sign in on its Config page.

Panel URLs are `http://192.168.96.61:8089/Panasonic.grid` and `http://192.168.96.61:8089/Marshall.grid`.
The downloads contain the panel-host URL and HTTP image paths.
The host also serves CameraBridge at `http://192.168.96.61:8089/`.
Open CameraBridge in either panel uses that address.

## Host access

The host accepts the configured TouchDrive address and the Windows address only.
It serves fixed panel, image, health and administration routes.
It forwards login tokens to the backend.
Configuration requests still require a backend administrator.
It does not expose service shutdown, simulator CGI ports or arbitrary files.

The isolated bench uses plain HTTP.
Use [security guidance](security.md) for remote production administration.
If a firewall blocks the host, an administrator can add this scoped rule:

```powershell
New-NetFirewallRule -DisplayName 'CameraBridge TD1C development panels' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress 192.168.96.61 -LocalPort 8089 -RemoteAddress 192.168.96.122 -Profile Any
```

## Stop or remove the host

1. Close the applicable CameraBridge panel tabs.
2. Press Ctrl+C in the panel-host terminal.
3. Remove its firewall rule if it is no longer required.

```powershell
Remove-NetFirewallRule -DisplayName 'CameraBridge TD1C development panels'
```

Do not remove Ross files or unrelated device connections.
Change bench addresses deliberately if the network configuration changes.
