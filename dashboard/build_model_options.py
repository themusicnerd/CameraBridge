"""Generate the web profile choices from the same catalog as native DashBoard."""
import html
import pathlib
import re
from backend.panasonic_models import MODELS,profile_id,label

def build():
    path=pathlib.Path(__file__).resolve().parents[1]/'web/admin.html'
    choices=[(profile_id(m),label(m)) for m in MODELS]
    choices.insert(0,choices.pop(next(i for i,c in enumerate(choices) if c[0]=='panasonic')))
    choices += [('panasonic-sim','Panasonic AW-HE130 — simulator'),('sony-sdk','Sony PXW-Z200 — Camera Remote SDK'),
                ('marshall-CV226','Marshall CV226 — hardware integration pending'),('marshall-CV228','Marshall CV228 — hardware integration pending'),('marshall-lab','Marshall CV228 — lab model')]
    options=''.join('<option value="'+html.escape(value,quote=True)+'">'+html.escape(caption)+'</option>' for value,caption in choices)
    source=path.read_text(encoding='utf-8')
    source,n=re.subn(r'(<select id="camprofile">).*?(</select>)',lambda m:m[1]+options+m[2],source,flags=re.S)
    if n!=1:raise ValueError('Camera profile selector missing')
    path.write_text(source,encoding='utf-8')
