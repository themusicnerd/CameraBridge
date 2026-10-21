# Native DashBoard validation — 21 October 2026

## Environment and method

Existing installed Ross DashBoard9.15.2, Windows AMD64, using the existing workspace. The application was not restarted and no Ross binaries/libraries were modified. The registered Windows `.grid` association identifies the supported launcher command as `C:\DashBoard\DashBoard.exe --launcher.openFile <file>`.

The deliverable Panasonic panel opened as a native tab. Temporary copies of the Panasonic and Marshall deliverables were then opened, changing only their backend URL to a loopback observation proxy on18089 and adding a success callback inside their existing status helper. The proxy forwarded state requests to the running CameraBridge backend on8088. It logged request method/path only; no passwords, tokens or request bodies were logged.

The extra callback fired only when the normal poll callback reached its final `Feedback refreshed` status. That path follows JSON parsing, camera lookup, label updates, parameter values and access updates. It supplies native ogScript execution evidence, not a screenshot or optical camera test.

## Observed evidence

Repeated native traffic included:

```text
Native DashBoard POST /api/state
Native DashBoard POST /probe/Panasonic-feedback-ok
Native DashBoard POST /api/state
Native DashBoard POST /probe/Marshall-feedback-ok
```

The success paths occurred repeatedly. The accessibility tree also identified the deliverable Panasonic tab and the temporary probe tabs. The backend continued reporting two independent Panasonic emulators and one Marshall lab model, all simulated. No camera was physically connected.

## Passed scope

- Native OGLML file loading in DashBoard9.15.2.
- Native ogScript API initialisation and recurring timer operation.
- Native asynchronous HTTP state requests and JSON parsing.
- Both manufacturers' normal parameter/label update callback paths reaching completion.

## Still pending

- Visual layout, clipping, touchscreen hit targets and actual TD1C scaling. Window capture continues to fail with `FrameArrived timed out: timed out waiting on channel`.
- Manual sign-in and authenticated native controls. Account count was zero at the last check; a local password prompt has been opened for the operator.
- Motion/preset safety through real native interaction, real-camera control, exact Marshall serial protocols, and Carbonite/Preset-bus delegation.

The temporary probe files and observer are development intermediates under `work/`, not shipped panels or production dependencies. Their success does not change the unverified hardware status in the feature matrix.
