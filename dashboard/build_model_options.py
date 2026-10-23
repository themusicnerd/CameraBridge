"""Generate the web profile choices from the same catalog as native DashBoard."""
import html
import json
import pathlib
import re
from backend.panasonic_serial import MODEL as SERIAL_MODEL
from backend.panasonic_models import MODELS,profile_id,label

def build():
    path=pathlib.Path(__file__).resolve().parents[1]/'web/admin.html'
    source=path.read_text(encoding='utf-8')
    if 'id="camera-catalog"' in source:
        catalog=[dict(manufacturer='Panasonic',model=m,driver='panasonic') for m in MODELS]+[dict(manufacturer='Panasonic',model=SERIAL_MODEL,driver='panasonic-serial'),dict(manufacturer='Sony',model='PXW-Z200',driver='sony-sdk'),dict(manufacturer='Marshall',model='CV226',driver='marshall-pending'),dict(manufacturer='Marshall',model='CV228',driver='marshall-pending')]
        source,n=re.subn(r'(<script id="camera-catalog" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(catalog)+m[2],source,flags=re.S)
        if n!=1:raise ValueError('Camera catalog missing')
        path.write_text(source,encoding='utf-8');return
    choices=[(profile_id(m),label(m)) for m in MODELS]
    choices.insert(0,choices.pop(next(i for i,c in enumerate(choices) if c[0]=='panasonic')))
    choices += [('panasonic-sim','Panasonic AW-HE130 â€” simulator'),('sony-sdk','Sony PXW-Z200 â€” Camera Remote SDK'),
                ('marshall-CV226','Marshall CV226 â€” hardware integration pending'),('marshall-CV228','Marshall CV228 â€” hardware integration pending'),('marshall-lab','Marshall CV228 â€” lab model')]
    options=''.join('<option value="'+html.escape(value,quote=True)+'">'+html.escape(caption)+'</option>' for value,caption in choices)
    source=path.read_text(encoding='utf-8')
    source,n=re.subn(r'(<select id="camprofile">).*?(</select>)',lambda m:m[1]+options+m[2],source,flags=re.S)
    if n!=1:raise ValueError('Camera profile selector missing')
    path.write_text(source,encoding='utf-8')
