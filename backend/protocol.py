"""AW-HE130 protocol subset. See docs/panasonic-aw-he130.md for provenance."""
from dataclasses import dataclass, asdict
import re

@dataclass(frozen=True)
class Parameter:
    id: str
    label: str
    low: int
    high: int
    write: str
    query: str
    reply: str
    width: int = 2
    base: int = 16
    units: str = 'native'
    modes: tuple = ()
    dependency: str = ''
    allowed: tuple = ()

    def validate(self, value):
        if type(value) is not int or not self.low <= value <= self.high:
            raise ValueError(f'{self.id}: expected integer {self.low}..{self.high}')
        if self.allowed and value not in self.allowed:
            raise ValueError(f'{self.id}: unsupported enumeration')
        return value

    def encode(self, value):
        self.validate(value)
        return self.write + (f'{value:0{self.width}X}' if self.base == 16 else f'{value:0{self.width}d}')

    def decode(self, response):
        pattern = re.escape(self.reply) + ('[0-9A-Fa-f]' if self.base == 16 else '[0-9]') + '{' + str(self.width) + '}'
        if not re.fullmatch(pattern, response):
            raise ValueError(f'{self.id}: malformed query reply')
        return self.validate(int(response[len(self.reply):], self.base))

    def metadata(self):
        data = asdict(self)
        for key in ('write','query','reply','width','base'):
            data.pop(key)
        return dict(data, writable=True, readback=True)

# Native wire ranges; red/blue 0x096 represents zero on HE130, not zero gain.
PANASONIC = {
    p.id: p for p in [
        Parameter('iris_auto','Iris mode: 0 manual / 1 auto',0,1,'#D3','#D3','d3',1,10),
        Parameter('iris','Iris',0x555,0xFFF,'#AXI','#AXI','axi',3,16,dependency='iris_auto=0'),
        Parameter('focus_auto','Focus: 0 manual / 1 auto',0,1,'#D1','#D1','d1',1,10),
        Parameter('zoom','Zoom position',0x555,0xFFF,'#AXZ','#AXZ','axz',3),
        Parameter('focus','Focus position',0x555,0xFFF,'#AXF','#AXF','axf',3,dependency='focus_auto=0'),
        Parameter('red_gain','Red gain (150 = reference)',0,300,'ORI:','QRI','ORI:',3,dependency='wb_mode=2,3'),
        Parameter('blue_gain','Blue gain (150 = reference)',0,300,'OBI:','QBI','OBI:',3,dependency='wb_mode=2,3'),
        Parameter('wb_mode','WB: ATW 0 / A 2 / B 3 / 3200K 4 / 5600K 5 / VAR 9',0,9,'OAW:','QAW','OAW:',1,10,allowed=(0,2,3,4,5,9)),
        Parameter('detail','Detail: 0 off / 1 on',0,1,'ODT:','QDT','ODT:',1,10),
    ]
}

def movement(pan=0, tilt=0, zoom=0, focus=0):
    for value in (pan,tilt,zoom,focus):
        if type(value) is not int or not -49 <= value <= 49:
            raise ValueError('Movement axes must be integers -49..49')
    return [f'#PTS{50+pan:02d}{50+tilt:02d}',f'#Z{50+zoom:02d}',f'#F{50+focus:02d}']

def preset(number, store=False):
    if type(number) is not int or not 1 <= number <= 100:
        raise ValueError('Preset must be 1..100 (wire 00..99)')
    return f'#{"M" if store else "R"}{number-1:02d}'
