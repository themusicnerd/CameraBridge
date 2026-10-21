# Feedback model

Each parameter has an actual value and an optional requested value.
Its record also contains range, required mode, query time, command time and error information.
Simulator cameras use the same record format and have a simulator label.

| State | Meaning |
|---|---|
| `unknown` | No valid query has established the value |
| `pending` | A write is in the queue |
| `confirmed` | An independent query returned the expected value |
| `mismatch` | The query returned a different value |
| `error` | The write or query failed |
| `stale` | The previous confirmed value is too old |

Stale detection uses the greater of ten seconds and three configured poll intervals.
The interface keeps the last actual value and its age.
It does not replace actual feedback with the requested value.
Dependent writes require fresh confirmed mode information.

Camera workers query parameters individually.
Native panels read central state approximately once per second.
Panel reads do not add camera queries.
The default delay after a query round is four seconds.

Shot completion is not part of parameter confirmation.
Preset state remains `last command sent, unverified`.
An emulator result does not establish physical camera motion or optical matching.
