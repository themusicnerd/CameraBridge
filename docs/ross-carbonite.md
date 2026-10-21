# Carbonite integration

The development frame is a Carbonite Ultra at 192.168.96.123.
The TouchDrive address is 192.168.96.122.
The default camera 1 port is now 19011.
Earlier bench captures used port 19010.
Use the [camera setup procedure](camera-setup.md) for numbered physical Panasonic endpoints.
The procedure below describes the separate simulator relay.

## Recorded device

| Setting | Value |
|---|---|
| Device slot | 0 |
| Device name | Beauty |
| Device type | Camera |
| Driver | PIVOTCam_1.1 |
| Address | 192.168.96.61 |
| TCP port | 19011 |
| Input | 1 |
| Input device | Beauty-S0 |
| Channel | 1 |
| Pan and tilt inversion | No |

The operator created the initial device and input association.
Its original Cambot_1.0 driver sent ASCII camera traffic.
Changing the driver did not replace that connection.
The test slot was then recreated with PIVOTCam_1.1.
Input 1 and channel 1 were restored.
Other device slots were not changed.

## Test results

Initialization, focus-mode inquiry and variable movement reached the emulator.
Some movement packets were rejected.
Shot store, shot recall and an operator-triggered Custom Control recall reached the emulator.
Physical camera behavior and actual bus selection remain unverified.
See [lab protocol](ross-lab-protocol.md) for packet evidence.

The release relay rejects physical camera targets.
Do not point this development relay at production equipment.

## References

- [Ross PTZ device setup](https://help.rossvideo.com/carbonite-device-db/Topics/Devices/Robo-Cam/Ross-PTZ.html)
- [Ultra camera Custom Controls](https://help.rossvideo.com/ultra/Topics/Operation/CustomControls/Events-Camera.html)
