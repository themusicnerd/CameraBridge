# Feedback model

Each parameter includes ID/label, native range/units, dependencies, writable/readback capability, actual value, requested value, last successful query, last command, confirmation and error. `None` plus `unknown` means startup has not established an actual value. Simulator parameters use the same model but their camera is explicitly labelled simulated.

Accepted UI writes set `requested` and `pending`, then enter a coalescing queue. The worker revalidates mode and ownership, transmits, queries and parses. Matching actual values become `confirmed`; differing replies become `mismatch`; failed writes become `error`. A successful command echo is insufficient. Presets remain `last command sent, unverified` because activity/completion readback is not implemented.

Snapshot responses compute age and replace old confirmed labels with `stale` after the larger of 10 seconds and three configured poll intervals. Last actual values remain visible with their age; they are not silently replaced by requested values. Fresh confirmed mode state is required before dependent writes.

Workers poll one parameter at a time and yield to movement. Default completed-round delay is four seconds; adjust `poll_seconds` (1..60) in configuration. Panel polling reads central state once per second and does not increase camera traffic. External camera value changes appear on subsequent queries. Query priority, per-family refresh rates and Panasonic notification subscription are pending.

Transport connection, query response and physical camera action are different evidence. Marshall lab state cannot establish real RS485 acknowledgement or current settings. Ross Program/Preset/positioner fields remain unverified until actual switcher feedback is integrated.
