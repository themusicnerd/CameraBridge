# Troubleshooting

| Symptom | Check and action |
|---|---|
| Address is already in use | Stop the previous CameraBridge instance, or select unused configured ports |
| Service does not start | Read the terminal error; check configuration and operating system support |
| Camera is unavailable | Check its address, network connection, enabled flag and supported model |
| Value is stale | Check network access and the time of the last valid query |
| Control is disabled | Sign in; check camera lock, ownership, feedback and required manual mode |
| Red or blue gain is disabled | Select a supported manual white-balance memory |
| Typed value disappears | Press Enter promptly, or use the fader and large adjustment buttons |
| Jog stops while held | The watchdog expires without new valid movement input |
| Movement is rejected after a stop | Return pan/tilt and zoom to neutral before new input |
| Positioner response is irregular | Record VISCA packets and rejection times; continuous movement acceptance is incomplete |
| Push/pull has no effect | Its separate command mapping is not established |
| Shot command succeeds but framing is unknown | Physical shot completion is not implemented |
| Marshall camera does not respond | The release has only a Marshall lab model |
| Serial TCP connects but the camera does not answer | Check framing, baud, address, polarity and exact-model protocol |
| Open CameraBridge does not open a browser | Open the displayed backend address manually |
| TouchDrive web page cannot connect | Check the panel host, allowed source address and scoped firewall rule |
| Exported panel has no logo | Run the panel export command again in its current location |
| Login fails after restart | Sign in again; restart removes memory-only sessions |

Do not use a missing serial reply as proof that a camera is offline.
Do not retry an uncertain shot store or menu action automatically.
Do not guess equipment passwords.

## Collect a support record

1. Record the application version and package target.
2. Record the camera model, firmware and network arrangement.
3. Download Diagnostics from the web interface.
4. Save the exact error and test sequence.
5. Remove sensitive information before you share the record.

Use `CameraBridge diagnostic --output host-report.json` for host facts.
Do not include `credentials.sqlite`, passwords or session tokens.
