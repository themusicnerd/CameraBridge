# Panasonic AK-HC1800G and AW-PH360N

Use this profile when a USR-IOT gateway connects the network to the AW-PH360N RS-422 control port.
The camera connects to the head with its existing camera cable.
The gateway carries serial data over a TCP connection.

## Configure The Gateway

1. Open the USR-IOT gateway web interface.
2. Select transparent TCP server mode.
3. Set the serial interface to RS-422.
4. Set the serial rate to 9600 baud.
5. Set 8 data bits, no parity, and 1 stop bit.
6. Set flow control to None.
7. Note the gateway IP address and TCP server port.

Use the same head, camera, and cable settings that worked with the AW-RP120.
CameraBridge does not change the head protocol switches or camera protocol menu.
Gateway settings are entered on the gateway, not sent by CameraBridge.
The gateway web port and serial TCP port are separate settings.

## Add The Camera

1. Open the CameraBridge setup page.
2. Select Add Camera.
3. Select Panasonic in Manufacturer.
4. Select AK-HC1800G + AW-PH360N in Model.
5. Enter the gateway address in USR Gateway IP.
6. Enter its serial server port in Gateway TCP Port.
7. Set Camera Number and Carbonite Input.
8. Set the TSL address for this camera.
9. Wait for All Changes Saved.

Each enabled serial camera must use a separate gateway IP and TCP port pair.
Different cameras can use different TCP ports.
A gateway with several serial channels can use one IP address and a different port for each channel.
Use port 19010 plus Camera Number for the Carbonite PIVOTCam device.
For example, camera 2 uses PIVOTCam TCP port 19012.
This PIVOTCam port is separate from the gateway serial port.

In native DashBoard, select the combined Panasonic camera and head profile.
Enter the gateway IP and TCP port in the camera connection fields.
Save the setup and apply it.
Use the current CameraBridge.grid file for this profile.

## Paint Coverage

This profile does not have the full AK-HC1800G paint command set.
It has red gain, blue gain, detail, iris mode, iris commands, and One Shot.
Master gain, shutter, master pedestal, separate channel pedestals, gamma, matrix, and other camera menu controls are not mapped.
Use the camera or its existing control panel for those settings.

## Available Controls

| Function | Behavior |
| --- | --- |
| Pan and tilt | Separate PH360 speed commands |
| Zoom and focus jog | Head lens speed commands |
| Stop | Neutral pan, tilt, zoom, and focus commands |
| Presets | Store and recall shots 1 through 50 |
| Iris and iris mode | Head commands; reported as Sent |
| Red and blue gain | Camera commands with independent query feedback |
| Detail | Camera command with query feedback |
| One Shot | AWB command; completion is not reported |
| Tally | Red tally command; lamp feedback is not available |

The selected profile does not provide autofocus mode, WB mode selection, or preset recall speed.
On this head, the D1 control is a lens extender command, not autofocus.
CameraBridge does not send D1 as an autofocus command.
Set the required paint mode on the camera before a gain adjustment.

A serial head command does not provide a required acknowledgement.
Sent means that CameraBridge wrote the command to the TCP connection.
It does not confirm motor movement, shot completion, iris position, or the tally lamp.
CameraBridge uses a camera identification reply to check the camera connection.
A TCP connection alone does not mark the camera online.

The driver uses Panasonic Convertible Protocol version 3.05.
See [Panasonic serial protocol](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE50_120_SERIAL/ConvertibleProtocol.pdf), pages 2 to 6 and 29 to 32.
The software tests use a TCP gateway fixture.
Physical checks for this camera and head remain to be completed.
