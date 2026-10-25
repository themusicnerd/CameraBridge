"""Shared staged numeric entry popup for native camera controls."""
from build_panels import node,field,task

def build(root,parameters):
    from aura_layout import button
    # Register mouse handlers at panel scope, with explicit component targets.
    for component in list(root.iter('param')):
        for handler in list(component.findall("ogscript[@handles='onmousedown']")):
            component.remove(handler);root.append(handler)
    node(parameters,'param',oid='number_value',name='New Value',type='STRING',value='',access=1,widget=3,maxlength=24)
    popup=node(root,'popup',id='number_popup',name='',left=460,top=80,width=1,height=1,group='camera-number-entry',style='bdr:none;bg#25282e;')
    body=node(popup,'abs',width=460,height=540,style='bg#2c3037;bdr:line;bdr#49a8d8;')
    for key,initial,top,height,size,colour in [('number_title','Enter Value',12,32,22,'ffffff'),('number_limits','Range',48,28,15,'ffffff'),('number_error','',150,44,14,'ef929f')]:
        node(parameters,'param',oid=key,name=key,type='STRING',value=initial,access=1,widget=100)
        display=field(body,key,16,top,428,height,100)
        display.set('style',f'size:{size};fg#{colour};bg#2c3037;bdr:none;')
    entry=field(body,'number_value',16,84,428,64,3);entry.set('style','size:26;txt-align:center;w.keyboard:disabled;')
    for i,digit in enumerate('789456123'):
        button(body,digit,16+(i%3)*110,202+(i//3)*66,102,"numberDigit('"+digit+"');",58)
    button(body,'Delete',346,202,98,'numberDelete();',58)
    button(body,'Clear',346,268,98,"params.setValue('number_value',0,'');",58)
    button(body,'+ / -',346,334,98,'numberSign();',58)
    button(body,'0',16,400,322,"numberDigit('0');",58)
    button(body,'Cancel',16,474,208,'numberCancel();',52)
    button(body,'Enter',236,474,208,'numberApply();',52,'49a8d8')
