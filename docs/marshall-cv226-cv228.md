# Marshall CV226 and CV228

The native Marshall panel controls a synthetic lab model.
It does not transmit CV226 or CV228 serial commands.
Confirmed feedback means confirmed lab state only.

The production command profile is disabled.
Do not substitute commands from a CV620, CV610 or CV420 profile.
An exact-model command list and firmware record are required.

## Prepare the command record

1. Record each camera model and firmware version.
2. Obtain the applicable command list from Marshall.
3. Record the camera ID and baud rate from its menu.
4. Check the serial framing against the model manual.
5. Capture one setting change and its query reply.
6. Record both directions, time and visible camera result.
7. Repeat the test at the range limits.

The quick reference specifies eight data bits, no parity and one stop bit.
The baud rate is selectable.
A menu camera ID does not establish the serial address encoding.
The provisional VISCA constructor permits addresses 1 through 7, but production registration remains disabled.

Use an authorized serial monitor or an external RS485 tap.
The TCP capture tool cannot monitor an application's COM port by itself.
Do not interpret absent acknowledgements as proof of an offline camera.

## References

- [CV228 product information](https://www.marshall-usa.com/cameras/CV228/)
- [CV226 and CV228 manual](https://www.marshall-usa.com/pdf/CV228-manual.pdf)
- [CV226 quick reference](https://marshall-usa.com/pdf/CV226-Quick-Reference-Guide.pdf)
- [Marshall software](https://www.marshall-usa.com/software/)
