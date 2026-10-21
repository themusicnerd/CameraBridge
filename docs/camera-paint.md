# Paint snapshots

A paint snapshot records confirmed parameter values from one camera.
It includes camera ID, model, name, notes, time and simulator status.
Zoom and focus position are excluded.
Values without a recent valid query are excluded.

## Capture values

1. Open CameraBridge in the browser.
2. Sign in.
3. Select **Paint snapshots**.
4. Select the camera.
5. Enter a snapshot name.
6. Select **Capture**.
7. Check the saved values and simulator label.

The service saves `snapshots.json` in the data directory.
A repeated name replaces the previous snapshot with that name.
Save a backup first if the previous record is required.

Snapshot recall, import, comparison and cross-camera matching are incomplete.
Equal native values do not establish equal optical results.
Do not use a lab snapshot as a physical camera reference.
