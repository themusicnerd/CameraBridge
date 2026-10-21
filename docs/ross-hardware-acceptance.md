# Carbonite / TouchDrive acceptance still required

User-authorized development equipment: Carbonite Ultra 192.168.96.123 and TD1C 192.168.96.122. No switcher device slot, camera/input mapping, Custom Control or TD1C software installation has been changed by CameraBridge work so far.

## Documented Custom Control configuration

The current [Ultra Camera Custom Control event reference](https://help.rossvideo.com/ultra/Topics/Operation/CustomControls/Events-Camera.html) documents the following under **Devices → Camera** in the custom-control event editor:

| Action | Fields to configure |
|---|---|
| Camera Halt All | Select the camera device |
| Recall Shot | Camera, channel, Absolute/Reset change type and shot number |
| Recall Shot Fast | Same camera/channel/shot selection, fastest recall |
| Store Shot | Camera, channel, Absolute/Reset change type and shot number |

After a working gateway has been validated, an operator example is: add Recall Shot, choose the device associated with Panasonic 1, select its verified channel, use Absolute, enter Shot 20, and save the custom control. A corresponding halt custom control should target the same camera. Store examples must be tested only on an expendable preset and with remote stores explicitly allowed. Exact menu labels must be checked against the frame's installed version.

These are documented configuration examples, **not hardware-tested CameraBridge macros**. Carbonite Custom Controls are not assumed to issue arbitrary HTTP. Paint look/select/group actions still need a documented external pathway or a verified native translation. Normal switcher Program/ME memories are distinct from physical camera shots and CameraBridge paint snapshots.

## Before enabling a hardware listener

1. Record frame firmware, DashBoard/plugin versions, occupied ports/device slots and current input/device mappings. Back up the switcher set using its normal supported workflow.
2. Capture initialization, inquiries, joystick axes/neutral, halt, preset store/recall and both Program/Preset source changes from a working modern gateway. Confirm raw TCP framing, addressing, ACK sockets and completion timing.
3. Implement and test physical Panasonic preset completion (notification or other documented evidence), supported inquiries and any additional required commands. Do not reuse the emulator's instantaneous completion claim.
4. Add a separately reviewed LAN listener restricted to the frame's management address. The existing lab server intentionally cannot be used on a LAN or against a physical camera.
5. Use an unused device slot/input association. Test with emulators first, then a physical camera within a controlled movement area. Preserve original mappings for rollback.
6. Verify that Preset selects the intended camera, Program alone does not, old camera movement stops before handover, stale packets cannot move the new camera, and neutral input is required after a switch/fault.
7. Test simultaneous PT/zoom, all directions, deadbands, focus-mode push behaviour, presets, disconnect/watchdog stopping, service shutdown/restart and camera outages.
8. Run real Recall Shot/Recall Shot Fast/Halt/Store Custom Controls, including an unassigned input and invalid preset. Confirm normal switching is unaffected.

If native delegation follows additional buses, a documented real bus-feedback adapter is required to enforce Preset-only following. The simulator's bus API is not such an adapter. Panel Follow/Live Assist page navigation is also distinct from physical positioner delegation. Physical TouchDrive knob mapping remains a separate research item.
