"""Native Aura-inspired operator layout, separate manufacturer-specific panels."""
import pathlib
import xml.etree.ElementTree as ET
from build_panels import COMMON,HERE,node,script,task,field

BG='25282e';SURFACE='2c3037';BUTTON='494f5b';PURPLE='7433bd';BLUE='49a8d8'
SHORT={'iris_auto':'IRIS AUTO','focus_auto':'AUTO FOCUS','iris':'IRIS','zoom':'ZOOM POSITION','focus':'FOCUS POSITION',
       'red_gain':'RED GAIN','blue_gain':'BLUE GAIN','wb_mode':'WHITE BALANCE','detail':'DETAIL',
       'exposure_auto':'AUTO EXPOSURE','brightness':'BRIGHTNESS','gain':'GAIN','agc_limit':'AGC LIMIT',
       'shutter':'SHUTTER','black_level':'BLACK LEVEL','gamma':'GAMMA ×10','colour':'COLOUR','sharpness':'SHARPNESS',
       'dnr':'NOISE REDUCTION','mirror':'MIRROR','flip':'FLIP','digital_zoom':'DIGITAL ZOOM ×10'}

def label(parent,text,x,y,w,h=24,id=None,colour='e2e4e9',size=14):
    return node(parent,'label',name=text,left=x,top=y,width=w,height=h,style=f'fg#{colour};size:{size};txt-align:west;',**({'id':id} if id else {}))
def button(parent,text,x,y,w,code,h=44,colour=BUTTON,id=None):
    b=node(parent,'button',name=text,left=x,top=y,width=w,height=h,buttontype='push',style=f'bg#{colour};fg#ffffff;bdr:none;size:14;',**({'id':id} if id else {}));task(b,code);return b
def card(parent,x,y,w,h):return node(parent,'abs',left=x,top=y,width=w,height=h,style=f'bg#{SURFACE};bdr:line;bdr#383d45;')
def feedback(parent,key,x,y,w):label(parent,'unknown · never read',x,y,w,26,'actual_'+key,'a9bbc8',11)
def vertical(parent,key,x,y,w=140,h=440):
    box=card(parent,x,y,w,h)
    label(box,SHORT[key],10,10,w-20,26,size=13)
    entry=field(box,key,10,43,w-20,34,6);script(entry,f"changed('{key}');",'onchange')
    slider=field(box,key,32,90,w-64,h-165,4);script(slider,f"changed('{key}');",'onchange')
    feedback(box,key,10,h-66,w-20)
    return box
def horizontal(parent,key,x,y,w=480):
    box=card(parent,x,y,w,86);label(box,SHORT[key],12,8,w-24,20,size=13)
    s=field(box,key,10,31,w-116,29,3);script(s,f"changed('{key}');",'onchange')
    e=field(box,key,w-98,31,86,29,6);script(e,f"changed('{key}');",'onchange')
    feedback(box,key,12,60,w-24)
    return box
def jog_button(parent,text,x,y,w,h,axes):
    b=node(parent,'button',name=text,left=x,top=y,width=w,height=h,style=f'bg#202328;fg#c8cbd3;bdr:line;bdr#30353d;size:20;')
    script(b,'jog('+','.join(map(str,axes))+');','onmousedown')
    script(b,'stop();','onmouseup');script(b,'stop();','onmouseexit');return b

def build(manufacturer,defs):
    pana=manufacturer=='Panasonic'
    root=ET.Element('abs',{'contexttype':'opengear','id':'_top','name':'CameraBridge '+manufacturer,
        'virtualwidth':'1366','virtualheight':'800','width':'1366','height':'800','gridaspect':'false','gridsize':'10',
        'keepalive':'false','style':f'bg#{BG};fg#e2e4e9;size:14;'})
    api=node(root,'api');api.text=f"var CB_MANUFACTURER = '{manufacturer}';\n"+COMMON
    meta=node(root,'meta');params=node(meta,'params')
    for oid,name,value,widget,access in [('bridge','Backend URL','http://127.0.0.1:8088',3,1),('username','Username','',3,1),('password','Password','',4,1),('camera','Camera ID','pana1' if pana else 'marshall1',3,0),('confirmation','Type OVERWRITE','',3,1),('shot_name','Shot name','',3,1)]:
        node(params,'param',oid=oid,name=name,type='STRING',value=value,widget=widget,access=access,maxlength=256)
    for oid,name,low,high,value in [('speed','Jog speed',1,49,12),('store','Store armed',0,1,0),('shot_number','Shot number',1,100,1)]:
        node(params,'param',oid=oid,name=name,type='INT32',value=value,access=1,constrainttype='INT_RANGE',constraint=f'{low};{high};')
    for key,p in defs.items():
        n=node(params,'param',oid=key,name=SHORT.get(key,p.label),type='INT32',value=p.low,access=0)
        if p.allowed:
            n.set('constrainttype','INT_CHOICE')
            choices={0:'ATW',2:'AWB A',3:'AWB B',4:'3200K',5:'5600K',9:'VAR'} if key=='wb_mode' and pana else {}
            for v in p.allowed:node(n,'constraint',key=v).text=choices.get(v,str(v))
        else:
            n.set('constrainttype','INT_RANGE')
            n.set('constraint',f'{p.low};{p.high};'+('-150;150;' if pana and key in ('red_gain','blue_gain') else ''))
    node(meta,'timer',id='bridge_tick',rate=200,autostart='true')
    node(meta,'timertask',timerid='bridge_tick',tasktype='ogscript').text='tick();'
    script(root,"highlightPage('"+('PTZ' if pana else 'Paint')+"');poll();",'onload');script(root,"if(cbToken)request('command',{camera:selected(),action:'stop',data:{}},null);",'onclose')

    header=card(root,8,8,1350,64)
    label(header,'CameraBridge / '+manufacturer,16,8,385,24,size=19)
    label(header,'AW-HE130 · PTZ & paint' if pana else 'CV226 / CV228 · paint & setup',16,35,385,20,colour='abb1bd',size=12)
    pages=['PTZ','Presets','Paint','TD1C','Config'] if pana else ['Paint','Exposure','OSD','Config']
    for i,name in enumerate(pages):node(header,'reveal',id='nav_'+name.lower(),name=name,targetid='page_'+name.lower(),left=425+i*80,top=11,width=74,height=42,style=f'bg#{PURPLE if i==0 else BUTTON};fg#ffffff;bdr:none;')
    logo_width=131 if pana else 177
    node(header,'image',src=(HERE/'assets'/('panasonic.png' if pana else 'marshall.png')).as_uri(),left=1332-logo_width,top=10,width=logo_width,height=45)
    label(root,'Camera identification pending',126,80,950,24,'identity',size=16)
    label(root,'SIMULATOR / awaiting feedback',126,105,1120,22,'connection','a9bbc8',12)
    rail=card(root,8,80,106,650)
    label(rail,'CAMERAS',10,12,90,22,size=12)
    for i in range(6):button(rail,'—',8,43+i*65,90,f'cameraAt({i});',58,PURPLE if i==0 else BUTTON,'camera_pick_'+str(i))
    button(rail,'Next',8,445,90,'nextCamera();')
    field(rail,'camera',8,499,90,30)
    button(rail,'Refresh',8,540,90,'poll();')
    button(rail,'STOP',8,591,90,'stop();',48,'91414b')
    tabs=node(root,'tab',left=126,top=135,width=1224,height=595,tabposition='none',delay='false',onchange='highlightPage(String(this.getTitleAt(this.getSelectedIndex())));')
    content={name:node(tabs,'abs',id='page_'+name.lower(),name=name,width=1224,height=595,style=f'bg#{BG};') for name in pages}

    if pana:
        ptz=content['PTZ']
        label(ptz,'PAN / TILT CONTROL',16,0,445,28)
        button(ptz,'Touch control DISABLED',16,34,440,'touchEnable();',42,BUTTON,'touch_enable')
        pad=card(ptz,16,87,440,396)
        for text,x,y,axes in [('↖',8,8,(-1,1,0,0)),('UP',152,8,(0,1,0,0)),('↗',296,8,(1,1,0,0)),('LEFT',8,137,(-1,0,0,0)),('RIGHT',296,137,(1,0,0,0)),('↙',8,266,(-1,-1,0,0)),('DOWN',152,266,(0,-1,0,0)),('↘',296,266,(1,-1,0,0))]:jog_button(pad,text,x,y,136,121,axes)
        button(pad,'+\nSTOP',152,137,136,'stop();',121,'282c33')
        label(ptz,'Jog speed',16,495,120,25);field(ptz,'speed',139,491,240,32,3);field(ptz,'speed',385,491,71,32,6)
        label(ptz,'Release / exit stops · 0.9s backend watchdog',16,535,445,30,colour='a9bbc8',size=12)
        for key,x,top,bottom in [('iris',490,'CLOSE','OPEN'),('zoom',730,'WIDE','TELE'),('focus',970,'NEAR','FAR')]:
            box=card(ptz,x,0,220,560);label(box,SHORT[key],14,12,192,28)
            field(box,key,14,49,192,32,6)
            if key=='iris':
                button(box,top,14,93,192,"send('write',{parameter:'iris',value:1365},null);",40)
                button(box,bottom,14,438,192,"send('write',{parameter:'iris',value:4095},null);",40)
            else:
                axes=(0,0,-1,0) if key=='zoom' else (0,0,0,-1)
                jog_button(box,top,14,93,192,40,axes)
                jog_button(box,bottom,14,438,192,40,tuple(-v for v in axes))
            s=field(box,key,73,146,74,279,4);script(s,f"changed('{key}');",'onchange')
            feedback(box,key,14,488,192)
            if key in ('iris','focus'):
                mode=key+'_auto'
                button(box,'Manual',14,519,92,f"send('write',{{parameter:'{mode}',value:0}},null);",32)
                button(box,'Auto',114,519,92,f"send('write',{{parameter:'{mode}',value:1}},null);",32)
        presets=content['Presets']
        label(presets,'CAMERA SHOTS / BANK 01–20',14,4,900,28)
        for i in range(20):button(presets,f'{i+1:02d}\nShot {i+1}',14+(i%5)*186,48+(i//5)*110,178,f'preset({i+1});',100,BUTTON,'shot_'+str(i+1))
        side=card(presets,954,48,254,500)
        label(side,'RECALL / STORE',14,12,226)
        label(side,'0 recall / 1 store',14,49,226);field(side,'store',14,80,226,36,6)
        label(side,'Overwrite confirmation',14,135,226);field(side,'confirmation',14,168,226,38)
        label(side,'Type OVERWRITE before storing.',14,210,226,45,colour='a9bbc8',size=12)
        label(side,'NAME A SHOT',14,286,226)
        field(side,'shot_number',14,320,64,36,6);field(side,'shot_name',84,320,156,36)
        button(side,'Save shot name',14,370,226,'renamePreset();')
        label(side,'Recall activity stays unverified\nuntil camera completion is known.',14,435,226,50,colour='a9bbc8',size=12)
        paint=content['Paint']
        for i,key in enumerate(['red_gain','blue_gain','iris','detail']):
            # Iris has its main feedback ID on the PTZ page; secondary view shares parameter only.
            if key=='iris':continue
            vertical(paint,key,16+i*188,35,172,450)
        horizontal(paint,'wb_mode',780,35,420)
        horizontal(paint,'iris_auto',780,139,420)
        horizontal(paint,'focus_auto',780,243,420)
        # Focus/zoom labels are on PTZ; mode labels above complete the feedback contract.
        label(paint,'R/B gain is displayed as -150..+150; native wire range remains 0..300.',16,511,1180,30,colour='a9bbc8',size=12)
        label(paint,'Additional paint families enable only when their model profile is verified.',16,546,1180,30,colour='a9bbc8',size=12)
        td=content['TD1C'];label(td,'TOUCHDRIVE / CARBONITE CAMERA BRIDGE',20,18,1160,32,size=19)
        label(td,'Connection not verified',20,71,1160,48,'ross_state')
        for i,text in enumerate(['Preset bus selects the target camera; Program-only changes must not retarget it.',
                                  'Physical 3D positioner: simultaneous variable pan / tilt / zoom.',
                                  'Camera handover: stop previous target; reject stale movement.',
                                  'Custom Controls: native Recall Shot / Recall Shot Fast / Store Shot / Halt All.',
                                  'Hardware gateway validation is separate from local simulator success.']):label(td,text,20,151+i*58,1150,45)
        button(td,'LAB: select on Preset',20,484,270,"labBus('preset');",48,BLUE)
        button(td,'LAB: change Program only',308,484,270,"labBus('program');",48)
        label(td,'Explicit simulator events only — these buttons do not change the switcher.',20,548,1150,30,colour='a9bbc8',size=12)
    else:
        paint=content['Paint']
        for i,key in enumerate(['red_gain','blue_gain','black_level','gamma','colour','sharpness','brightness','gain']):vertical(paint,key,8+i*152,34,142,495)
        label(paint,'LAB MODEL · serial command map is not yet verified for CV226/CV228.',12,547,1180,34,colour='d7bb8c')
        exposure=content['Exposure']
        for i,key in enumerate(['wb_mode','exposure_auto','agc_limit','shutter','dnr','mirror','flip','digital_zoom']):horizontal(exposure,key,12+(i%2)*608,22+(i//2)*135,588)
        osd=content['OSD'];label(osd,'OSD / CAMERA SETUP',18,16,1100,30,size=18)
        label(osd,'Fixed cameras · no mechanical pan/tilt',18,58,1100,30,colour='a9bbc8')
        for key,text,x,y in [('menu','MENU',222,125),('up','UP',222,193),('left','LEFT',60,261),('enter','ENTER',222,261),('right','RIGHT',384,261),('down','DOWN',222,329),('back','BACK',222,397)]:button(osd,text,x,y,150,"send('osd',{key:'"+key+"'},function(r){if(r)status(r.status);});",58)
        label(osd,'RS485 adapter / address / firmware',650,143,520,28)
        label(osd,'Currently a synthetic LAB model.\nNo serial packets are transmitted.\nExact gateway and camera firmware pending.',650,196,520,150,colour='a9bbc8')

    config=content['Config']
    label(config,'CONNECTION / OPERATOR LOGIN',22,18,1100,32,size=19)
    label(config,'Backend',22,81,160);field(config,'bridge',200,73,650,40)
    label(config,'Username',22,141,160);field(config,'username',200,133,300,40)
    label(config,'Password',22,201,160);field(config,'password',200,193,300,40)
    button(config,'Sign in',200,258,145,'login();',48,BLUE)
    button(config,'Sign out',355,258,145,"stop();cbToken='';cbTouchEnabled=false;status('Signed out');",48)
    button(config,'Lock camera',200,330,145,"send('lock',{value:true},null);")
    button(config,'Unlock camera',355,330,145,"send('lock',{value:false},null);")
    label(config,'Configuration, diagnostics and paint snapshots: separate administration interface.',22,429,1150,40,colour='a9bbc8')
    label(config,'SIMULATOR values confirm simulator state. Hardware acceptance is separate.',22,487,1150,40,colour='d7bb8c')
    label(root,'Starting…',126,743,1220,44,'status','b9c5cf',12)
    path=HERE/f'SW-{manufacturer}-Camera-Control.grid'
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path
