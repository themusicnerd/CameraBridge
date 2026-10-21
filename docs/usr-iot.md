# USR-IOT serial gateway

The adapter model and serial settings are not established.
No adapter configuration was changed during the recorded tests.
The serial transport is not connected to a production Marshall profile.

## Check an adapter

1. Record its exact model and firmware.
2. Obtain its model manual.
3. Back up its current configuration.
4. Check the TCP mode, address and port.
5. Check baud rate, data bits, parity and stop bits.
6. Check RS485 polarity and automatic direction control.
7. Check termination, bias and unique camera addresses.
8. Check that TCP data has no added protocol wrapper.
9. Test one camera before a shared camera bus.

Use one SerialBus object for each shared connection.
Its lock covers request, reply and turnaround time.
Reads and wait times have limits.
The transport connects again on the next request after a connection failure.
It does not automatically repeat an uncertain write.
A second store or menu action could have an unwanted result.

Use a checksum only if the exact protocol requires one.
TCP connection status and camera response status are separate facts.
