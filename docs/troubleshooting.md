# Troubleshooting

**Port already used:** stop the previous CameraBridge process or deliberately change the configuration. Do not terminate unrelated services or use a Ross reserved port.

**Panel shows unknown/stale:** confirm the backend URL and authentication, then inspect web diagnostics. CGI emulator URLs are localhost18080/18081. Simulator values should populate after the first query round; cached state is not a substitute for a successful query.

**Slider read-only:** confirm login, camera lockout, fresh feedback and the required manual mode. Red/blue gain is unavailable in ATW. A disabled manual control is expected safety behaviour.

**Jog ends while held:** the native panel requests a bounded jog. The 900ms watchdog intentionally expires if no new valid input arrives. No indefinite mouse-hold heartbeat is implemented.

**Marshall hardware does not respond:** the production command map is disabled. The visible panel controls are a lab model, not evidence of an enabled RS485 camera driver. Obtain the exact-model protocol before hardware testing.

**RS485 TCP connected but no camera reply:** check transparent mode, polarity, serial framing, address and response support. Do not mark a camera offline solely from absent ACKs.

**SSH access denied:** obtain credentials/keys through an authorised path. Do not guess vendor passwords. VNC/FTP availability does not establish Linux shell permissions.

**DashBoard panel load error:** record installed DashBoard version and full debug/error text. Both panels have loaded and processed feedback in local9.15.2. Regenerate with `python dashboard/build_panels.py`; XML tests alone do not establish runtime support. Do not patch Ross libraries. The Windows computer-use screenshot helper times out, so visual/touch checks remain pending despite native callback evidence.

**Shutdown/network failure:** a stop attempt cannot guarantee delivery across a failed link. Use the camera's independent control path to verify neutral before resuming. The service does not replay queued movement after restart.
