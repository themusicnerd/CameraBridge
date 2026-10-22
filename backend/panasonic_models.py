"""Panasonic CGI compatibility catalog, grouped by protocol family.

Model grouping follows Bitfocus's MIT-licensed Panasonic camera module.
Wire commands come from Panasonic's interface specifications. See docs/panasonic-models.md.
"""
FAMILIES={
    'HE40':('AW-HE35','AW-HE38','AW-HE40','AW-HE48','AW-HE58','AW-HE65','AW-HE70','AW-HN38','AW-HN40','AW-HN65','AW-HN70','AW-SFU01'),
    'HE42':('AW-HE42','AW-HE68','AW-HE75'),
    'UE70':('AW-UE63','AW-UE65','AW-UE70','AW-UN70'),
    'UE150':('AW-HE145','AW-UE100','AW-UE150','AW-UE155','AW-UN145'),
    'HE50':('AW-HE50','AW-HEF5'),
    'HE60':('AW-HE60',),'HE120':('AW-HE120',),'HE130':('AW-HE130','AW-HR140'),
    'HE2':('AW-HE2',),'UE4':('AW-UE4',),'UB300':('AK-UB300',),
    'CX350':('AG-CX350','AG-CX200','AJ-UPX360','AJ-CX4000','AJ-UPX900'),
    'generic':('Other',),
}
MODELS={model:family for family,models in FAMILIES.items() for model in models}

def capabilities(model):
    family=MODELS[model]
    fixed=family in ('UB300','CX350')
    return {'pan_tilt':not fixed,'pan_tilt_type':'digital' if family in ('HE2','UE4') else 'none' if fixed else 'mechanical',
            'zoom_jog':not fixed,'focus_jog':not fixed and family not in ('HE2','UE4'),
            'preset_max':0 if fixed else 9 if family=='HE2' else 100,
            'hardware_tested':model=='AW-HE40',
            'compatibility':'HE40 tested on hardware; other models require camera acceptance',
            'gain_display_divisor':5 if family in ('HE40','HE42','UE70','HE50','HE60') else 1}

def profile_id(model):
    return 'panasonic' if model=='AW-HE130' else 'panasonic:'+model

def label(model):
    if model=='Other':return 'Panasonic — other CGI camera (verify controls)'
    if model=='AW-HEF5':return 'Panasonic AW-HE50 with AW-HEF5 upgrade'
    if model=='AW-SFU01':return 'Panasonic AW-HE40 with AW-SFU01 upgrade'
    return 'Panasonic '+model+(' — digital PTZ' if model in ('AW-HE2','AW-UE4') else '')
