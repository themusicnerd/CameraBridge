# Feature and test status

This table separates software tests from physical equipment acceptance.

| Feature | Current evidence | Remaining work |
|---|---|---|
| AW-HE130 CGI driver | Emulator query and write tests | Physical camera tests |
| Panasonic iris, focus, zoom and paint subset | Independent query confirmation | Firmware and optical checks |
| Panasonic shot store and recall | Native Carbonite commands reach emulator | Physical shot completion |
| TouchDrive positioner | Variable pan, tilt and zoom reach emulator | Packet rejection and continuous response |
| Positioner push/pull | No separate command observed | Mapping and tests |
| Carbonite Custom Control Recall Shot | Operator test and emulator capture | Physical camera result |
| Recall Fast, Halt All and Custom Control Store Shot | Not yet tested through equipment | Native event tests |
| Actual Preset-bus following | Simulator event state machine only | Real bus feedback adapter |
| Native Panasonic and Marshall panels | Native TD layout, login and write tests | Physical camera use |
| Large touch controls | 1920 × 1080 VNC checks | Operator touch acceptance |
| Open setup link | Panel script and host route tests; native address popup | External TouchDrive browser launch |
| Camera setup | Browser add, edit, remove, numbering and export test | Physical installation acceptance |
| Numbered PIVOTCam endpoints | Fixed target, controller restriction and shot tests | Physical Panasonic acceptance |
| Sony PXW-Z200 | Disabled configuration entry; official SDK research | SDK access, driver and hardware tests |
| Marshall paint and OSD | Synthetic lab model | Exact CV226/CV228 command map |
| Shared RS485 transport | Serialized TCP transport | Adapter and camera acceptance |
| Paint snapshot capture | Confirmed values saved | Recall, comparison and matching |
| Configuration changes | Validated pending file | Explicit restart required |
| User roles and sessions | API tests | Production hardening |
| Desktop tray and control panel | Owned process lifecycle test | User desktop acceptance |
| Platform packages | Native workflow build and package tests | User installation acceptance |
| TouchDrive backend installation | Not performed | Vendor permission and host tests |
| Production use | Not accepted | Complete equipment acceptance |

See the release workflow for the result of each platform build.
See [lab protocol evidence](ross-lab-protocol.md) for the actual Carbonite tests.
Raw JSON captures and the native screen images remain in this documentation directory.

The application has no HE40 or HE120 production profile.
The application has no production Marshall driver.
A generic TCP connection does not establish camera compatibility.
