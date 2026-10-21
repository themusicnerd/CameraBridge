# Installation and rollback

## Windows development

Use Python 3.11+ and run from the project directory. There are no third-party packages. Check ports8088,18080,18081 before starting. `python -m backend.server --init-user admin` prompts for credentials; `python -m backend.server --lab` starts local emulators and backend. The PowerShell launcher under `deployment/windows` is provided for interactive use; ensure `python.exe` resolves to an installed interpreter.

The development service may already be running in this chat at <http://127.0.0.1:8088>. Create a user in a separate terminal if needed. A second server instance will fail to bind rather than take over existing listeners. Ctrl+C stops the foreground service and attempts camera neutral commands. No Windows service, scheduled task or startup entry is installed automatically.

Use `--lab --visca-lab` to include the local TCP controller endpoints on 19010/19011. Remote simulator preset stores additionally require `--visca-allow-store`. The Windows launcher enables the VISCA lab but leaves remote stores disabled by default. Regenerate the native panels with `python dashboard/build_panels.py` after moving the project so manufacturer-logo URLs are valid at the new location. See `ross-lab-protocol.md` for the end-to-end controller demonstration.

## Generic x86-64 Linux

Check `uname -m`, `python3 --version`, storage, user permissions, loopback and listening ports. Copy source to an approved user-owned directory, e.g. `~/camerabridge`. Create private configuration and runtime directories:

```sh
mkdir -p ~/.config/camerabridge ~/.local/share/camerabridge
chmod 700 ~/.config/camerabridge ~/.local/share/camerabridge
cp config.example.json ~/.config/camerabridge/config.json
python3 -m backend.server --storage ~/.local/share/camerabridge --init-user admin
python3 -m backend.server --config ~/.config/camerabridge/config.json --storage ~/.local/share/camerabridge --lab
```

Remove `--lab` only after configuring actual supported cameras. The service unit intentionally omits lab mode. It assumes code under `~/camerabridge` and Python at `/usr/bin/python3`; adapt paths after checking the host. After foreground acceptance, install it as an independent user service:

```sh
mkdir -p ~/.config/systemd/user
cp deployment/linux/camerabridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start camerabridge
systemctl --user status camerabridge
journalctl --user -u camerabridge
```

Enable on login only after validation with `systemctl --user enable camerabridge`. Do not assume lingering or boot persistence is allowed. Do not enable it on TD1C without the explicit deployment decision.

## TD1C

For native panels on the TD with the backend/emulators on Windows, use [TouchDrive development panel hosting](touchdrive-panel-host.md). That arrangement does not install the backend on the TD. The compatibility requirements below apply to a future backend installation on the TD itself.

First complete `td1c-compatibility.md`. Architecture, OS, runtime, writable paths, service manager, persistent storage, vendor permissions and update survival are unresolved. A self-contained executable has not been built. Do not modify Ross partitions, libraries, DashBoard binaries or boot configuration. Do not use root just because it is available.

## Configuration and security

Change `bind`/`port` and trusted CIDRs in a reviewed config file, then restart with `--config`. Lab mode requires loopback and exclusively simulated cameras. For remote panels, remove lab mode, explicitly permit the development PC/TD1C management addresses and use an HTTPS reverse proxy. CGI emulators have no authentication and must remain loopback. Do not expose them to the network.

Administration saves to `runtime/config.pending.json`; this does not silently change running camera assignments. Back up the old configuration and deliberately restart using the pending file after reviewing it. Camera changes require correct host/port and supported model profiles. A bad config fails startup.

## Backup / rollback / removal

Stop CameraBridge before copying its configuration, `runtime/snapshots.json` and private credential database. Keep credentials in an access-controlled backup and exclude them from diagnostic bundles and source control. Record the code revision. Restore a previous code directory and matching configuration, then restart and re-query cameras. Never replay saved motion.

For Linux removal: `systemctl --user disable --now camerabridge`, remove only the CameraBridge user-unit file, and `systemctl --user daemon-reload`. Retain or separately archive its user-owned data; do not delete Ross files. For Windows, stop the process; no system installation has been made. Do not delete the working project until needed configurations/snapshots are backed up.
