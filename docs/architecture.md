# Architecture

The Windows/Linux development process owns the REST adapter, central Engine, one worker and I/O lock per camera, and memory-only sessions. Lab mode additionally starts independent Panasonic HTTP servers. Separate native DashBoard panels and the administration page share the same state.

```
Panasonic .grid ─┐
Marshall .grid ──┼── authenticated HTTP adapter ── Engine ── camera workers
Web admin ───────┘                                  │          ├─ Panasonic CGI
                                                   │          └─ Marshall LAB model
                                                   └─ state + bounded diagnostic events
```

Commands are protocol-independent until they reach a driver. Paint writes coalesce by parameter. Workers recheck ownership, generation, lockout and dependent camera modes immediately before transmission. Camera I/O failures do not terminate other camera workers. Polling yields to movement.

The movement watchdog uses monotonic deadlines. New jog input expires after 900ms unless refreshed by valid input. It invalidates queued movement before attempting neutral commands. No movement is restored from persistent storage. Stop commands bypass ownership but require API authentication.

One shared `SerialBus` instance is required per physical RS485 bus. Its lock covers the complete request/response/turnaround interval. The exact-model Marshall driver is currently fail-closed and not registered as a production camera driver.

The service uses only the Python standard library. Python was chosen for protocol work, portability and zero downloaded application dependencies. Go is attractive for a single executable and predictable deployment; no CPU/RAM comparison has yet been measured. Porting a tested protocol core is preferable to presenting estimated resource usage as measurements. The supplied Linux unit limits CPU/RAM; these are policy settings, not measured consumption.

Current limitations: the stdlib HTTP server is a local engineering service, not an internet-facing hardened server; no WebSocket transport; no applied live configuration reload; diagnostic events are bounded in memory; exhaustive lifecycle/fault tests remain outstanding. Use a trusted management network and an HTTPS reverse proxy for remote operation.
