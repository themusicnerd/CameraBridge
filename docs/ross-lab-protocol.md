# Lab VISCA protocol

The optional listener accepts address-1 serial VISCA over TCP.
It translates a limited command set to Panasonic CGI emulator commands.
It is not a production gateway.

## Start the listener

Source command:

```sh
python -m backend.server --lab --visca-lab --ensure-admin
```

Package command:

```sh
./CameraBridge --lab --visca-lab --ensure-admin
```

The default endpoints are 127.0.0.1:19011 for pana1 and 127.0.0.1:19012 for pana2.
Add `--visca-allow-store` only for an intentional emulator store test.
Native panel stores retain their separate OVERWRITE check.

## Start the bench relay

```sh
./CameraBridge ross-relay --bind 192.168.96.61 --frame 192.168.96.123 --port 19011 --output capture.jsonl
```

On Windows, use `.\CameraBridge.exe`.
For source use, replace the executable and subcommand with `python tools/ross_dev_relay.py`.
The relay accepts one configured frame address and one active connection.
It checks lab mode and a loopback Panasonic emulator target.
It records both directions and stops the test at the capture size limit.
It disconnects unsupported initial framing without an invented reply.

## Implemented messages

| Function | Message or rule |
|---|---|
| Address assignment | `88 30 01 FF` returns `88 30 02 FF` for one virtual camera |
| Broadcast interface clear | `88 01 00 01 FF` returns the same bytes |
| Addressed interface clear | `81 01 00 01 FF` returns `90 50 FF` |
| Movement | Variable pan/tilt, zoom and focus speeds |
| Focus | Auto/manual mode and mode inquiry |
| Shot | Zero-based wire index maps to operator shot 1 through 100 |
| Command success | `90 41 FF` and `90 51 FF` for accepted commands |
| Unsupported command | `90 60 02 FF` |
| Command not executable | `90 60 41 FF` |

Frames end with FF and have a 16-byte limit.
The reader supports fragmented and combined TCP data.
The movement queue has limits and replaces older matching movement entries.
Non-neutral movement can be rejected after 300 milliseconds in the queue.
Neutral stops do not expire.
Stops and movement have priority over polling.
The watchdog interval is 900 milliseconds.
Speed conversion is software normalization, not measured optical calibration.

## Target selection

The lab follower accepts an authenticated simulator bus event.
It does not infer actual bus state from VISCA packets.
A Preset event changes the lab target and stops the previous target.
A Program event does not change the target.
Both pan/tilt and zoom neutral input are required after a target change or stop.
Old selection epochs cannot move the new target.

A fixed numbered camera endpoint does not use the lab target selection gate.
Pan/tilt input does not require a separate zoom-neutral packet on that endpoint.
Repeated confirmed speed commands update the watchdog without another camera request.

## Equipment evidence

- Initial CamBot traffic was `02 30 30 30 20 4E 43 03`.
- PIVOTCam advanced after the address-assignment reply.
- Focus-mode inquiry returned emulator manual mode.
- Paint inquiries 35, 39, 4A, 4B and 4C are unsupported.
- The positioner sent positive and negative pan, tilt and zoom values.
- The retained first movement window had 51 accepted pan/tilt and 20 accepted zoom commands.
- That window also had rejected movement and a watchdog stop.
- No distinct push/pull, focus or focus-mode command was identified in that sequence.
- Shot 20 tests produced three stores and two recalls at the emulator.
- A later operator-triggered Custom Control sent another shot 20 recall.

The Custom Control recall arrived at Unix time 1792584354.1276023.
Its frame was `81 01 04 3F 02 13 FF`.
The emulator received `#R19`.
The protocol does not identify the user action that triggered a recall.
Custom Control origin comes from the operator's test report.

Raw evidence is in ross-carbonite-first-capture.json, ross-positioner-first-test.json and ross-preset-first-test.json.
These captures do not establish physical camera completion.
The emulator changes velocity axes but does not integrate them into physical positions.

## Reference

[Sony E0421001M](https://pro.sony/support/res/manuals/E042/3230148ee903c204b912cca5c2c3f5aa/E0421001M.pdf) defines the serial initialization replies.
