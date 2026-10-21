# Camera tally lights

Tally control defaults to enabled for each camera, including cameras from an older configuration.
Enable or disable it in **Camera setup** with the camera's tally checkbox.
Save and apply the setup to keep the setting.
Disabled cameras ignore manual and TSL tally requests.

## Panasonic AW-HE130

The driver enables the tally input with `#TAE1`.
It sets the red lamp with `#DA0` or `#DA1`.
It queries `#DA` to confirm the lamp state.
Program tally controls the red lamp.
Preview is shown in the requested state but does not drive a green lamp in this release.

## Sony PXW-Z200

The SDK adapter has red and green tally property support.
The PXW-Z200 capability table does not list those external lamp properties.
A PXW-Z200 tally request therefore reports unsupported unless the camera exposes the documented properties.
The camera's recording lamp cannot currently serve as an external tally lamp through this SDK profile.
CameraBridge never starts recording as a tally workaround.
See [Sony camera setup](sony-pxw-z200.md).

## Manual test

1. Sign in to CameraBridge.
2. Open the camera card or its native panel.
3. Select **Tally ON** or **PROGRAM**.
4. Check the actual camera lamp and reported tally state.
5. Select **Tally OFF**.
6. Confirm that the lamp switches off.

The Sony dashboard also has a preview test button.
The state distinguishes requested values, readback, errors and unsupported controls.
Manual test requests can be replaced by the next TSL input.

## TSL UMD 3.1 receiver

1. Open **Camera setup**.
2. Enable the TSL receiver.
3. Set the listen IP and UDP port.
4. Set the allowed switcher source IP.
5. Set each camera's TSL address.
6. Save and apply the setup.
7. Configure the switcher to send TSL UMD 3.1 messages to CameraBridge.
8. Test each program transition and lamp readback.

The default UDP port is 5727.
The default camera address is its Carbonite input number minus one.
For example, video input 1 maps to TSL address 0.
An explicit camera address overrides this mapping.
Valid TSL addresses are 0 through 126.
Tally 1 is program; tally 2 is preview.
The receiver rejects packets from other source IP addresses and malformed messages.
Only complete 18-byte TSL 3.1 messages are accepted.
TSL 4 and TSL 5 are not supported by this receiver.

The receiver remains off until its network settings are configured.
This is separate from the per-camera enable option, which defaults to on.
State is retained until another message or manual request arrives.
There is no input-loss timeout for switchers that send only on a change.
On normal shutdown, the bridge attempts to clear lamps that it confirmed as active.
A broken network can prevent that command from reaching a camera.
Physical Carbonite tally transmission has not been accepted yet.

## API

Send an authenticated `POST /api/command` request:

```json
{"camera":"pana1","action":"tally","data":{"program":true,"preview":false}}
```

The normal command authentication and management-host restrictions apply.
Tally is independent of the operator's motion ownership lease.
It does not claim or move the camera.

## References

- [Panasonic IP interface specification](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE50_120_IP/HDIntegratedCamera_InterfaceSpecifications-E.pdf)
- [TSL UMD protocol specification](https://assets.ctfassets.net/vd4y94r5n5vv/2rcLXZWfZ6eOQ2MgEYa2QE/6b086201c7f1ed01f8ad926f0ef2c4d8/TSL_protocol_spec.pdf)
