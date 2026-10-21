# Marshall CV226 / CV228

References: [CV228 product page](https://www.marshall-usa.com/cameras/CV228/), [shared CV226/CV228 manual](https://www.marshall-usa.com/pdf/CV228-manual.pdf), [CV226 quick reference](https://marshall-usa.com/pdf/CV226-Quick-Reference-Guide.pdf) and [official software downloads](https://www.marshall-usa.com/software/). Reviewed on 21 October 2026.

These sources establish RS485/VISCA support and camera menu features. They do not by themselves supply the exact-model direct command/inquiry byte map used by every firmware revision. A command list for CV620, CV610 or CV420 must not be substituted for CV226/CV228.

The native panel exposes a **synthetic lab model** for white balance, exposure, image controls and OSD. Menu ranges informed some lab controls; labels explicitly identify unverified lab ranges. Confirmed lab feedback means confirmed simulator state only. It makes no claim about a serial query capability. The production Marshall class fails closed for writes, and production driver registration is disabled.

Before implementation: identify the third camera and all firmware, obtain the exact command list from Marshall, and record camera ID and baud from OSD. The quick reference documents 8 data bits, no parity, one stop bit, with selectable baud. The manual's camera-ID menu range must not be confused with a proven serial address encoding; current provisional VISCA constructor restricts 1..7 and is not enabled for hardware.

For official-application analysis, use an authorised serial-monitoring facility or an external RS485 tap. Record both request and response bytes, time, model, firmware, camera address and visible menu effect. Compare one setting at a time, including inquiry-only traffic and edge values. The included TCP receive capture is useful for a controller/gateway TCP stream; it cannot see the Windows application's COM-port traffic by itself. No proprietary application is bundled and no unverified bytes are transmitted.
