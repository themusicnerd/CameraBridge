# Panasonic AW-HE130 driver

Primary source: [HD Integrated Camera Interface Specifications v1.12, 27 April 2020](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE50_120_IP/HDIntegratedCamera_InterfaceSpecifications-E.pdf), linked from Panasonic's [protocol index](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/EN/top.html). Reviewed on 21 October 2026. Local research copies are not redistributed.

The implemented subset uses GET requests to `/cgi-bin/aw_ptz` for commands beginning `#` and `/cgi-bin/aw_cam` for paint commands, with URL-encoded `cmd` and `res=1`. `#` must be encoded as `%23`. Transport enforces a 130ms minimum interval between requests to one camera. HTTP success does not establish physical position or applied paint.

| Family | Write | Independent query |
|---|---|---|
| Pan/tilt speed | `#PTSpp tt` without space, each 01..99, neutral50 | Not treated as physical position readback |
| Zoom/focus speed | `#Znn` / `#Fnn`, neutral50 | Position queries are separate |
| Iris mode | `#D3n`, 0 manual,1 auto | `#D3` |
| Iris position | `#AXIhhh`, 555..FFF hex | `#AXI` |
| Focus mode | `#D1n` | `#D1` |
| Focus / zoom position | `#AXFhhh` / `#AXZhhh` | Same command prefix, without value |
| Red / blue gain | `ORI:hhh` / `OBI:hhh`, 000..12C | `QRI` / `QBI` |
| White-balance mode | `OAW:n` | `QAW` |
| Detail off/on | `ODT:n` | `QDT` |
| PTZ preset | `#Rnn` recall / `#Mnn` store | Completion/activity currently unverified |

These are implementation contracts, not a full transcription of the manufacturer specification. The preset UI numbers 1..100 map to wire 00..99. Red/blue gain wire150 represents reference zero for HE130. WB control codes for banks A/B differ from HE130 query codes; the driver translates the UI/query representation 2/3 to control1/2. An echo is never used to confirm a paint value: the query reply must parse and validate independently.

Manual iris/focus writes require fresh confirmed manual mode. Red/blue gain requires a fresh bank-A/B mode. ATW/preset-dependent writes are blocked rather than silently accepted.

Pending: additional paint families, shutter/gain mappings, AWB execution/notification processing, home, recall speed and model-specific HE40/HE120 profiles. NDI availability/licensing on those cameras is not established here and is independent of the CGI control path. No physical cameras are presently connected. Software fixtures and emulators cannot verify optical direction, actual movement, native menu limits, camera firmware differences or NDI support.
