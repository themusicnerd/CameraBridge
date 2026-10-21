# USR-IOT serial gateways

Exact adapter model, firmware, address, TCP port and serial settings remain unknown. No adapter was reconfigured or contacted in this work. Obtain the correct model manual before selecting TCP server/client modes or changing persistent settings.

`backend.drivers.SerialBus` supplies a reconnect-on-next-request TCP transport, a mutex covering send/read/turnaround, bounded reads, response timeout and configurable delay. Reuse one object for every camera on a shared bus. Do not instantiate a new bus object per camera sharing that endpoint. This transport is not yet wired to an approved production Marshall command profile.

Camera responsiveness and TCP connectivity are separate fields. A timeout leaves camera responsiveness unknown, not offline. Writes are not retried after an ambiguous timeout; a second non-idempotent command could repeat a store or menu action. Reply matching, ACK/completion socket handling and safe idempotent retry require the approved model profile. There is no invented CRC: use a checksum only if the actual protocol specifies it.

Commissioning must check baud, 8N1 where appropriate, RS485 two-wire polarity, automatic direction, turnaround, bias/termination, unique addresses, raw transparent TCP operation and no unwanted protocol wrapping. Back up the adapter configuration before any later authorised change. Test one camera before introducing a multidrop bus.
