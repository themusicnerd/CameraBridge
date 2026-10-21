# Carbonite Ultra / TouchDrive integration

Target frame: 192.168.96.123. Panel: 192.168.96.122. No device slots, inputs, Custom Controls or switcher state have been modified.

Ross's [PTZ setup sheet](https://help.rossvideo.com/carbonite-device-db/Topics/Devices/Robo-Cam/Ross-PTZ.html) documents a DashBoard gateway, PIVOTCam_1.1 device driver, one gateway port per camera, and video-input device/channel association. This sheet concerns Ross PTZ cameras; it does not establish that CameraBridge's as-yet-unimplemented endpoint is compatible.

For later approved native setup, the documented navigation is Configuration → Devices → Add Device → Camera, then Configuration → Inputs → External to associate the video source. Record the original settings and use unused slots. The switcher driver must ultimately point at a verified gateway endpoint; do not point a production driver at a generic raw VISCA listener merely because both use TCP.

## Discover the actual gateway protocol

1. Record Carbonite firmware and local/TD1C DashBoard versions. The current PTZ plugin manual documents serial VISCA over TCP; the exact frame's command sequence still requires capture.
2. Record an existing Ross camera gateway configuration if available, without changing it.
3. On the development PC run `python tools/tcp_capture.py --port 19000 --output work/ross-receive.jsonl` (create `work/` first).
4. In a controlled test, configure an unused camera device slot to point at the PC capture endpoint only after the listener bind address/firewall have been deliberately chosen. The default listener is loopback and cannot receive remote traffic.
5. Capture connection setup, idle/inquiry traffic, each positioner axis, neutral, presets and camera changes. This receive-only listener emits no acknowledgements, so controller behaviour under missing replies is incomplete evidence.
6. Obtain the official gateway wire specification or capture both directions from a working gateway before implementing timing and response semantics.

No Preset/Program events are fabricated. A general statement that source selection jumps to camera controls is insufficient evidence for Preset-only physical-positioner delegation. Native delegation is retained. Program-only changes, bus-follow logic, camera handover and simultaneous pan/tilt/zoom require physical acceptance tests.

Custom Controls: use existing native robotic-camera actions only after they work through a verified gateway. The current Ultra reference documents Recall Shot, Recall Shot Fast, Store Shot and Halt All under Devices → Camera. Configuration examples and remaining physical tests are in `ross-hardware-acceptance.md`; they are not claimed as hardware-tested CameraBridge macros. Do not assume arbitrary HTTP is available. Paint snapshot recall/select/matching integration remains pending.

The lab-only serial VISCA/TCP bridge and Preset-only selection state machine are now implemented and simulator tested. See `ross-lab-protocol.md`. They do not yet receive actual switcher bus events or permit LAN/physical targets.

TouchDrive knob mapping is a research item. No undocumented hardware device access or panel-library modification has occurred.
