# Architecture

One Python process owns the central state engine.
Each camera has one worker and one input/output lock.
Native panels and the web interface read the same state.

```text
Native panels ---- authenticated HTTP ---- State engine ---- Panasonic CGI
Web interface ---/                           |
                                            +------------- Marshall lab model
Carbonite ---- restricted lab relay ---- VISCA listener ---/
```

The TouchDrive host can serve panels, images and the web interface.
It forwards a fixed set of HTTP requests to the local backend.
It preserves the login token for backend access checks.

Paint writes for the same parameter replace older queued writes.
Workers check ownership, generation, lock and required mode before transmission.
An independent query confirms a paint value.
A command echo does not confirm it.

The watchdog uses a monotonic clock.
It invalidates queued movement before it attempts neutral commands.
The application never restores movement from disk.
The lab VISCA listener stops its selected target when a controller connection ends.

The lab follower accepts explicit simulator bus events.
It requires fresh pan/tilt and zoom neutral input after a target change or stop.
It does not read the actual Carbonite bus.

One SerialBus object must serve each shared physical RS485 connection.
The production Marshall command profile is not registered.

The console service uses only the Python standard library.
The desktop interface uses PySide6 Essentials.
A QProcess instance owns the console child process.
A private standard-input pipe requests graceful shutdown.
Closing that pipe also stops the child.
Desktop settings are separate from the selected camera configuration.
A local user socket brings an existing control panel to the front.
Release packages include Python through PyInstaller.
The service is not an internet-facing production server.
CPU and memory acceptance limits require measurement on the target equipment.
