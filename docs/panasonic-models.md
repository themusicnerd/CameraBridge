# Panasonic camera profiles

Select the exact camera model when you add a camera.
Set its camera number, IP address, HTTP port, and Carbonite input.
The first default PIVOTCam endpoint is TCP 19011.
Each camera has a tally enable option. The default is enabled.

Do not use LAB mode with a real camera.
Clear **Simulator mode** in the desktop control panel before starting a mixed configuration.
Camera simulators can remain enabled in a hardware configuration.
The management interface still requires sign-in.

## Catalog

The catalog follows the [Bitfocus Panasonic module](https://github.com/bitfocus/companion-module-panasonic-ptz).
It includes these groups:

| Family | Models |
|---|---|
| HE2 | AW-HE2 |
| HE40 | AW-HE35, HE38, HE40, HE48, HE58, HE65, HE70; AW-HN38, HN40, HN65, HN70 |
| HE42 | AW-HE42, HE68, HE75 |
| UE70 | AW-UE63, UE65, UE70; AW-UN70 |
| UE150 | AW-HE145; AW-UE100, UE150, UE155; AW-UN145 |
| Other legacy PTZ | AW-HE50, HE60, HE120, HE130; AW-HR140 |
| UE4 | AW-UE4 |
| Fixed camera entries | AK-UB300; AG-CX350, CX200; AJ-UPX360, CX4000, UPX900 |
| Upgrade entries | AW-HEF5 for HE50; AW-SFU01 for HE40 |
| Other | A conservative CGI compatibility profile |

AW-HEF5 and AW-SFU01 are upgrades, not separate camera bodies.
Select their entries only for a camera with that upgrade.
Fixed camera entries disable PTZ, focus jog, and shot recall.
Their advanced camera controls are not implemented in this release.

## Available controls

HE130 and HE40 have lens, white-balance, red/blue gain, and detail profiles.
HE40 detail values are 0 for Off, 1 for Low, and 2 for High.
Its gain wire value 150 is the reference value.
Five wire units equal one menu step.

Other motorized PTZ profiles enable common CGI pan, tilt, zoom jog, and focus jog commands.
Common lens position and mode controls require valid camera feedback.
Advanced paint controls remain read-only until the model has a verified command profile.
The catalog does not implement every action in the Bitfocus module.
It does not establish physical acceptance for every listed model.

HE2 uses digital pan, tilt, and zoom.
It has no focus control and supports shots 1 through 9.
Iris feedback uses the HE2 `#GI` response.
The HE2 absolute zoom slider is unavailable. Use zoom jog buttons.
HE2 white-balance values are 0/3 ATW, 1 memory A, and 2 memory B.
Values 4 through 8 select 3200 K, 5600 K, 4500 K, 6000 K, and 2800 K.

UE4 is a conservative digital PTZ profile.
Focus jog and absolute lens position controls are disabled.
Check its digital zoom mode before testing movement.

## Replies and camera modes

An ER1 reply means that the queried command is unsupported.
An ER3 reply means that it is unavailable in the current camera state.
The service retries these queries in later polling rounds.
Unavailable controls remain read-only.
Timeouts, malformed replies, and other errors remain visible as failures.

HE40 can reject a neutral focus command while autofocus is active.
The driver accepts that rejection only after confirming autofocus.
A rejected manual-focus stop remains an error.

The tested HE40 firmware reports white-balance memory A as 2 and memory B as 3.
It accepts write values 1 and 2 for those memories.
HE130 uses the same control mapping.
HE2 uses its documented raw values.

Camera HTTP authentication is not implemented in the Panasonic transport.
Use a camera configuration that permits CGI access from the bridge on the development network.
Do not put a camera password in the configuration JSON.

## References and acceptance

The command references are Panasonic's [integrated camera interface specifications](https://eu.connect.panasonic.com/sites/default/files/media/document/2019-02/HDIntegratedCamera_InterfaceSpecifications-V1.07E.pdf)
and [HE2 interface specifications](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE2_IP/HE2_HDIntegratedCamera_InterfaceSpecifications-V1.00E.pdf).

The HE40 test used a camera at 192.168.96.124 on the development network.
It confirmed model identification, lens feedback, white-balance memory control, gain feedback, and red tally feedback.
The zoom test produced feedback within one native unit of the request.
The test restored the starting settings.
Pan/tilt movement, shot recall, and end-to-end Carbonite tally still require physical acceptance.
Test those functions before operational use.
