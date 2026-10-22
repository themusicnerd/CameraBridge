# CameraBridge Help

## 1. Connect the Equipment

1. Connect the CameraBridge computer, cameras, Carbonite, and TouchDrive to the control network.
2. Give each device a different IP address.
3. Use addresses on the same subnet, or use a router between subnets.
4. Start CameraBridge on the computer.
5. Select **Open Setup Page** in the control panel.
6. Sign in with an administrator account.

The camera IP is the address of the camera.
The bridge IP is the LAN address of the CameraBridge computer.
Do not enter `127.0.0.1` as the bridge address on Carbonite or TouchDrive.
That address refers to the device on which it is used.

## 2. Add a Camera

1. Select **Add Camera**.
2. Open the camera row.
3. Set **Camera Number** and **Camera Name**.
4. Select **Manufacturer** and **Model**.
5. Enter **Camera IP** and **Camera HTTP Port**.
6. Set **Carbonite Input** to the video input for this camera.
7. Set **TSL Address** to the address sent for that input.
8. Set **Camera Enabled** to On.
9. Set **PIVOTCam Enabled** to On if Carbonite will control the camera.
10. Wait for **All Changes Saved**.
11. Check that the camera row shows **Online**.

Changes save when you leave a text field or change a switch or list.
Keep the page open until saving is complete.
Select an IP link to open the device web interface.

For a Panasonic camera, enable IP control in the camera web interface.
The Panasonic CGI transport does not use a camera username or password.

For a supported Sony SDK camera, open **Sony Camera Access**.
Select the camera, enter its username and password, and read its SSH fingerprint.
Compare the fingerprint with the camera.
Read the Sony SDK terms and enable **Sony SDK Terms Accepted**.
Complete access data saves automatically.

## 3. Connect Carbonite

1. Open **Switcher and Tally Network Settings** in CameraBridge.
2. Set **Bridge Listen IP** to the computer LAN address.
3. Set **Carbonite IP** to the switcher address.
4. Set **PIVOTCam Enabled** to On.
5. Leave **Base Port** at `19010`, unless you need a different range.
6. In Carbonite DashBoard, open **Configuration > Devices**.
7. Add a camera device in a free Ethernet slot.
8. Select driver **PIVOTCam_1.1**.
9. Set the device IP to the CameraBridge computer LAN address.
10. Set the device port to the port for this camera.
11. Save the device.
12. Open **Configuration > Inputs > External**.
13. Assign the device to the camera video input.
14. Set the device channel to `1`.

Each CameraBridge endpoint uses VISCA address 1.
Each camera has its own TCP port.

| Camera Number | TCP Port With Base 19010 |
|---|---|
| 1 | 19011 |
| 2 | 19012 |
| 3 | 19013 |

Use **Export PIVOTCam Map** to check the assignments.
The Carbonite input number and camera number can be different.

## 4. Install the TouchDrive Panel

1. Keep CameraBridge and its panel host running on the Windows computer.
2. On TouchDrive, open a web browser.
3. Go to `http://192.168.96.61:8089/CameraBridge.grid` for this system.
4. Save the file as `CameraBridge.grid` in Downloads.
5. Wait for the download to finish.
6. In DashBoard, close the old CameraBridge tab.
7. If DashBoard asks to save the old tab, select **No**.
8. Select **File > Open File**.
9. Open `/home/touchdrive/Downloads/CameraBridge.grid`.
10. Select **File > Save As**.
11. Open the panel directory you want to use.
12. On this system, use `/data/bin/carbonite/DashBoard/CameraBrdge/`.
13. Save the file as `CameraBridge.grid`.
14. Replace the old file if DashBoard asks.
15. Open the saved file from the DashBoard File Navigator.

The panel download contains the bridge URL for this network.
Use the computer LAN address in this URL.
Keep the `assets` folder with a panel that uses local images.
The panel-host download uses images from CameraBridge, so it does not need a local assets folder.

To update the panel, repeat this procedure with the new file.
Do not save the old open tab over the new file.

## 5. Set Up TouchDrive

1. Connect TouchDrive to Carbonite.
2. Copy `CameraBridge.grid` to the DashBoard panel directory on TouchDrive.
3. Close an older CameraBridge tab without saving it.
4. Open the new panel file.
5. Set **Bridge URL** to the CameraBridge panel-host address.
6. Sign in and select the camera.
7. Select the camera source on Carbonite.
8. Select its camera control page.
9. Move the positioner a small distance, then release it.
10. Use **Stop** to stop movement from the CameraBridge panel.

For this development system, the panel-host URL is `http://192.168.96.61:8089`.
The setup page is `http://192.168.96.61:8089/` from TouchDrive.
The local setup page is `http://127.0.0.1:8088/` on the Windows computer.
The panel file is in `/data/bin/carbonite/DashBoard/CameraBrdge/` on this TouchDrive.

Use the **Presets** page to recall a camera shot.
Keep **Preset Overwrite Enabled** off unless you want Carbonite to store shots.
CameraBridge does not follow the Carbonite Preset bus automatically.

## 6. Set Up Tally

1. Open **Switcher and Tally Network Settings**.
2. Set **TSL Listen IP** to the bridge LAN address, or use `0.0.0.0` for all local interfaces.
3. Set **UDP Port** to `5727`, or to your chosen receive port.
4. Set **Switcher Source IP** to the Carbonite address.
5. Select **Tally 2 (Carbonite)** as the program indicator.
6. Set **TSL Receiver Enabled** to On.
7. In Carbonite DashBoard, open **Configuration > Devices**.
8. Add a **TSL UMD** device with driver **TSL 3.1**.
9. Set its IP to the bridge LAN address and its port to the receiver UDP port.
10. Select **UDP** transport.
11. Set **1 Second Update** to On, then save the device.
12. Match each camera **TSL Address** to the address sent by Carbonite.
13. Set **Tally Light Enabled** to On for each lamp you want to control.
14. Put a camera on Preview, then on Program.

A green camera row shows Preview. A red row shows Program.
Program has priority if both indicators are on.
**Camera Tally Lamp** shows feedback from the camera, when available.
An HE40 has a red lamp. Its Preview indicator does not turn that lamp green.

**TSL Receiving** means that valid packets arrived from the configured source.
**Waiting For Packets** means that the receiver is open but has no valid packets.
**TSL Stale** means that no valid packet arrived in the last 10 seconds.
TSL uses UDP. It does not have a persistent connection.
Some senders send a packet only when tally changes.

## 7. Sign-In and the Tray

The browser keeps its sign-in after a page refresh or service restart.
Select **Sign Out** to end that browser session.
Changing the account password ends its saved sessions.
Use **Access Settings > Authentication Required** to enable or disable sign-in.

Right-click the CameraBridge tray icon and select **Control Panel**.
Close the control panel to keep CameraBridge running in the tray.
Select **Quit** in the tray menu to stop it.

## Troubleshooting

| Indication | Action |
|---|---|
| Camera is not Online | Open its IP link. Check its address, port, power, and IP control setting. |
| Changes are not saved | Complete required fields. Use a unique camera number. Read the message above the camera list. |
| Positioner has no effect | Check the Carbonite device IP, TCP port, channel 1, and video input assignment. |
| TSL waits for packets | Check the destination IP, UDP port, sender address, protocol, and network firewall rule. |
| Lamp state is Unknown | Check camera feedback. Some camera profiles do not provide lamp control or readback. |
| TouchDrive cannot connect | Use the computer LAN address. Keep the panel host running on port 8089. |

[Carbonite device setup reference](https://help.rossvideo.com/carbonite-device-db/Topics/Devices/Robo-Cam/Ross-PIVOTCam.html)


