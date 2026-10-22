# Camera Setup and PIVOTCam Assignments

Use the [quick-start procedures](quick-start.md) for cameras, Carbonite, TouchDrive, panel installation, and tally.

## Edit Cameras

1. Open the CameraBridge setup page.
2. Sign in with an administrator account, if authentication is enabled.
3. Select **Add Camera**, or open an existing camera row.
4. Set the camera number, name, manufacturer, model, address, and port.
5. Set **Carbonite Input** and **TSL Address**.
6. Set the camera, tally, PIVOTCam, and preset overwrite switches as required.
7. Leave the edited text field.
8. Wait for **All Changes Saved**.

Changes save and apply automatically.
Camera numbers must be unique integers from 1 through 255.
The internal camera ID stays the same during edits.
Removing a camera does not renumber the remaining cameras.
Select an IP link to open its web interface.
A change to a camera address or protocol stops the old camera connection before starting the new one.
Name and tally-option changes keep the existing connection and TSL receiver.
A failed network change restores the previous configuration.
The editor keeps its field values while saving.

## PIVOTCam Ports

The TCP port is the base port plus the camera number.
The default base port is 19010.
Camera 1 therefore uses port 19011.
Every endpoint uses VISCA address 1.
Assign that endpoint to the matching video input on Carbonite.
Use **Export PIVOTCam Map** to download the assignments.

## Access and Tally

**Access Settings** controls whether authentication is required.
The default is enabled.
Browser sign-in persists until sign-out or an account password change.
Trusted-host checks apply in both modes.

**Switcher and Tally Network Settings** contains the receiver settings and packet status.
Red rows show Program. Green rows show Preview.
Camera lamp feedback is separate from the received TSL indicators.
An unknown lamp state is not shown as Off.

See [Panasonic model details](panasonic-models.md), [Sony access](sony-pxw-z200.md), and [tally](tally.md).
