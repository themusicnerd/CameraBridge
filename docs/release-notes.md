# CameraBridge 0.3.0rc24

This development release adds optional buffered interpolation for FreeD and XPression tracking output.
Enable Buffered Interpolation Enabled in Virtual Camera Tracking. Set the delay in seconds.
Existing outputs keep interpolation off until you enable it.

The converter timestamps head and lens replies separately and interpolates measured encoder counts.
It does not predict future movement. Stale feedback and read errors clear the buffer and stop output.
The setup page reports Buffering, Interpolating, and Holding Latest states.

Start with a 0.75-second buffer for testing. Match the video delay and check audio timing.
Interpolation does not add source measurements or exposure synchronization.
Read docs/unreal-live-logo.md for the HE130 to Unreal live logo workflow and the remaining venue checks.

This release also removes the bottom-bar toggle tooltip on TouchDrive.
The crest mesh, Unreal Lens File integration, and complete broadcast signal path still need preparation and rehearsal.

Windows x64 and Linux x64 packages are included.
