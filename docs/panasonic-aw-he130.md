# Panasonic AW-HE130

The driver implements the command subset in this table.
It does not implement every camera feature.

| Function | Write | Query |
|---|---|---|
| Pan/tilt speed | `#PTSpp tt`, without the space; neutral 50 | Physical position is not queried |
| Zoom speed | `#Znn`; neutral 50 | Separate position query |
| Focus speed | `#Fnn`; neutral 50 | Separate position query |
| Iris mode | `#D3n`; 0 manual, 1 auto | `#D3` |
| Iris position | `#AXIhhh`; hexadecimal 555 through FFF | `#AXI` |
| Focus mode | `#D1n`; 0 manual, 1 auto | `#D1` |
| Focus position | `#AXFhhh` | `#AXF` |
| Zoom position | `#AXZhhh` | `#AXZ` |
| Red gain | `ORI:hhh`; hexadecimal 000 through 12C | `QRI` |
| Blue gain | `OBI:hhh`; hexadecimal 000 through 12C | `QBI` |
| White-balance mode | `OAW:n` | `QAW` |
| Detail | `ODT:n`; 0 off, 1 on | `QDT` |
| Shot recall | `#Rnn` | Physical completion is not queried |
| Shot store | `#Mnn` | Physical completion is not queried |

The driver sends HTTP GET requests with URL-encoded `cmd` and `res=1` fields.
Commands that start with # use `/cgi-bin/aw_ptz`.
Other commands use `/cgi-bin/aw_cam`.
The driver encodes # as `%23`.
It waits at least 130 milliseconds between requests to one camera.

Shot numbers 1 through 100 map to wire numbers 00 through 99.
Red and blue gain value 150 is the reference value.
The panel displays that reference as zero.
White-balance query values 2 and 3 map to control values 1 and 2.

Manual iris and focus changes require fresh confirmed manual mode.
Red and blue changes require a fresh supported manual white-balance memory.
The driver queries values independently after writes.
HTTP success or a command echo does not confirm a physical value.

HE40 gain feedback and One Shot command delivery are supported.
Additional paint families remain incomplete.
Notification processing and physical shot completion are also incomplete.
The release does not establish NDI availability or licensing.

## References

- [Panasonic interface specification, version 1.12](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE50_120_IP/HDIntegratedCamera_InterfaceSpecifications-E.pdf)
- [Panasonic protocol index](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/EN/top.html)
