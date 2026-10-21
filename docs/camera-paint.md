# Paint snapshots and matching

Snapshot capture stores camera/model, friendly name, notes, timestamp, simulation marker and only recently queried confirmed paint values. Position zoom/focus are excluded. Storage is atomic JSON replacement in the runtime directory; no file is rewritten on polling or slider traffic.

Capture is available through the administration page and authenticated `/api/snapshot`. Existing names currently replace the previous snapshot with that name; use distinct names to preserve looks. Read/export is available from `/api/snapshots` with authentication.

Recall, duplicate, rename, snapshot import, side-by-side compare and group matching are pending. They are deliberately not represented as working buttons. A future recall implementation must check model compatibility, plan mode ordering, reject stale/unsupported data, report partial application and confirm each write. Never infer optical matching from equal manufacturer-native numbers. Lab snapshots must not be imported as real camera references.
