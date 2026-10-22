"""Native TD1C touch layout. A 1366x800 canvas leaves room for DashBoard chrome."""
import xml.etree.ElementTree as ET
from build_panels import COMMON,HERE,node,script,task,field

BG='25282e';SURFACE='2c3037';BUTTON='494f5b';PURPLE='7433bd';BLUE='49a8d8'
SHORT={'iris_auto':'IRIS MODE','focus_auto':'FOCUS MODE','iris':'IRIS','zoom':'ZOOM POSITION','focus':'FOCUS POSITION',
       'colour_temperature':'COLOUR TEMPERATURE',
       'red_gain':'RED GAIN','blue_gain':'BLUE GAIN','wb_mode':'WHITE BALANCE','detail':'DETAIL',
       'exposure_auto':'EXPOSURE MODE','brightness':'BRIGHTNESS','gain':'GAIN','agc_limit':'AGC LIMIT',
       'shutter':'SHUTTER','black_level':'BLACK LEVEL','gamma':'GAMMA ×10','colour':'COLOUR','sharpness':'SHARPNESS',
       'dnr':'NOISE REDUCTION','mirror':'MIRROR','flip':'FLIP','digital_zoom':'DIGITAL ZOOM ×10'}

def label(parent,text,x,y,w,h=26,id=None,colour='e2e4e9',size=15):
    return node(parent,'label',name=text,left=x,top=y,width=w,height=h,style=f'fg#{colour};size:{size};txt-align:west;',**({'id':id} if id else {}))

def button(parent,text,x,y,w,code,h=52,colour=BUTTON,id=None):
    b=node(parent,'button',name=text,left=x,top=y,width=w,height=h,buttontype='push',style=f'bg#{colour};fg#ffffff;bdr:none;size:16;',**({'id':id} if id else {}));task(b,code);return b

def card(parent,x,y,w,h):return node(parent,'abs',left=x,top=y,width=w,height=h,style=f'bg#{SURFACE};bdr:line;bdr#383d45;')

def entry(parent,key,x,y,w,h=48,widget=6):
    e=field(parent,key,x,y,w,h,widget);e.set('style','size:18;');return e

def feedback(parent,key,x,y,w):label(parent,'unknown · never read',x,y,w,30,'actual_'+key,'a9bbc8',12)

def fader(parent,key,x,y,w,h):
    # Documented WIDGET_VERTICAL_FADER, with a broad handle rather than a dot.
    f=field(parent,key,x,y,w,h,26)
    f.set('style','w.nospinner:true;w.labels:false;w.thumbcolor:#49a8d8;w.jumptoclick:false;size:16;')
    return f

def steps(parent,key,low,high,x,y,w):
    button(parent,'−',x,y,64,f"adjust('{key}',-1,{low},{high});",48)
    entry(parent,key,x+72,y,w-144)
    button(parent,'+',x+w-64,y,64,f"adjust('{key}',1,{low},{high});",48)

def vertical(parent,key,p,x,y,w=276,h=520):
    box=card(parent,x,y,w,h);label(box,SHORT[key],16,12,w-32,30,size=17)
    entry(box,key,16,50,w-32);fader(box,key,32,110,w-64,h-222)
    button(box,'−',16,h-100,80,f"adjust('{key}',-1,{p.low},{p.high});",52)
    button(box,'+',w-96,h-100,80,f"adjust('{key}',1,{p.low},{p.high});",52)
    feedback(box,key,16,h-38,w-32);return box

def horizontal(parent,key,p,x,y,w=572):
    box=card(parent,x,y,w,122);label(box,SHORT[key],16,8,w-32,26,size=16)
    steps(box,key,p.low,p.high,16,39,w-32);feedback(box,key,16,90,w-32);return box

def jog_button(parent,text,x,y,w,h,axes):
    b=node(parent,'button',name=text,left=x,top=y,width=w,height=h,style='bg#202328;fg#e2e4e9;bdr:line;bdr#383d45;size:22;')
    script(b,'jog('+','.join(map(str,axes))+');','onmousedown')
    script(b,'stop();','onmouseup');script(b,'stop();','onmouseexit');return b

def build(manufacturer,defs):
    pana=manufacturer=='Panasonic'
    root=ET.Element('abs',{'contexttype':'opengear','id':'_top','name':'CameraBridge '+manufacturer,
        'virtualwidth':'1366','virtualheight':'800','width':'1366','height':'800','gridaspect':'false','gridsize':'10',
        'keepalive':'false','style':f'bg#{BG};fg#e2e4e9;size:16;'})
    node(root,'api').text=f"var CB_MANUFACTURER = '{manufacturer}';\n"+COMMON
    meta=node(root,'meta');params=node(meta,'params')
    for oid,name,value,widget,access in [('bridge','Backend URL','http://127.0.0.1:8088',3,1),('username','Username','',3,1),('password','Password','',4,1),('camera','Camera ID','pana1' if pana else 'marshall1',3,0),('confirmation','Type OVERWRITE','',3,1),('shot_name','Shot name','',3,1)]:
        node(params,'param',oid=oid,name=name,type='STRING',value=value,widget=widget,access=access,maxlength=256)
    for oid,name,low,high,value in [('speed','Jog speed',1,49,12),('store','Store armed',0,1,0),('shot_number','Shot number',1,100,1)]:
        node(params,'param',oid=oid,name=name,type='INT32',value=value,access=1,constrainttype='INT_RANGE',constraint=f'{low};{high};')
    for key,p in defs.items():
        n=node(params,'param',oid=key,name=SHORT.get(key,p.label),type='INT32',value=p.low,access=0)
        if p.allowed and not (pana and key=='wb_mode'):
            n.set('constrainttype','INT_CHOICE')
            choices={0:'ATW',2:'AWB A',3:'AWB B',4:'3200K',5:'5600K',9:'VAR'} if key=='wb_mode' and pana else {}
            for v in p.allowed:node(n,'constraint',key=v).text=choices.get(v,str(v))
        else:
            n.set('constrainttype','INT_RANGE');n.set('constraint',f'{p.low};{p.high};'+('-150;150;' if pana and key in ('red_gain','blue_gain') else ''))
    node(meta,'timer',id='bridge_tick',rate=200,autostart='true')
    node(meta,'timertask',timerid='bridge_tick',tasktype='ogscript').text='tick();'
    for key in defs:
        listener=script(root,"changed('"+key+"');",'onchange');listener.set('oid',key);listener.set('element','0')
    script(root,"highlightPage('"+('PTZ' if pana else 'Paint')+"');poll();",'onload')
    script(root,"if(cbToken)request('command',{camera:selected(),action:'stop',data:{}},null);",'onclose')
    header=card(root,8,8,1350,80)
    label(header,'CameraBridge / '+manufacturer,16,10,325,28,size=21)
    label(header,'AW-HE130 · PTZ & paint' if pana else 'CV226 / CV228 · paint & setup',16,45,325,24,colour='abb1bd',size=14)
    pages=['PTZ','Presets','Paint','TD1C','Config'] if pana else ['Paint','Image','Exposure','OSD','Config']
    for i,name in enumerate(pages):node(header,'reveal',id='nav_'+name.lower(),name=name,targetid='page_'+name.lower(),left=350+i*112,top=12,width=104,height=56,style=f'bg#{PURPLE if i==0 else BUTTON};fg#ffffff;bdr:none;size:16;')
    launcher=node(header,'abs',id='bridge_launcher',left=920,top=12,width=180,height=56)
    help_button=node(launcher,'help',id='open_bridge',left=0,top=0,width=180,height=56,name='Open setup',title='CameraBridge setup',popupwidth=600,popupheight=180,style=f'bg#{BLUE};fg#ffffff;size:16;')
    help_button.text='<html>Set the backend URL on Config. Select Open CameraBridge again after feedback loads.</html>' 
    logo_width=164 if pana else 177
    node(header,'image',src=(HERE/'assets'/('panasonic.png' if pana else 'marshall.png')).as_uri(),left=1328-logo_width,top=15,width=logo_width,height=48)
    label(root,'Camera identification pending',164,100,1178,26,'identity',size=18)
    label(root,'SIMULATOR / awaiting feedback',164,130,1178,24,'connection','a9bbc8',14)
    rail=card(root,8,104,140,624);label(rail,'CAMERAS',10,10,120,26,size=14)
    for i in range(6):button(rail,'—',8,42+i*64,124,f'cameraAt({i});',54,PURPLE if i==0 else BUTTON,'camera_pick_'+str(i))
    button(rail,'Next',8,432,124,'nextCamera();',48);button(rail,'Refresh',8,492,124,'poll();',48)
    button(rail,'STOP',8,552,124,'stop();',64,'a23d4c')
    tabs=node(root,'tab',left=164,top=164,width=1186,height=564,tabposition='none',delay='false',onchange='highlightPage(String(this.getTitleAt(this.getSelectedIndex())));')
    content={name:node(tabs,'abs',id='page_'+name.lower(),name=name,width=1186,height=564,style=f'bg#{BG};') for name in pages}
    if pana:
        ptz=content['PTZ'];label(ptz,'PAN / TILT CONTROL',12,0,408,28,size=17)
        button(ptz,'Touch control DISABLED',12,36,408,'touchEnable();',48,BUTTON,'touch_enable')
        pad=card(ptz,12,96,408,344)
        positions=[('↖',0,0,(-1,1,0,0)),('UP',1,0,(0,1,0,0)),('↗',2,0,(1,1,0,0)),('LEFT',0,1,(-1,0,0,0)),('RIGHT',2,1,(1,0,0,0)),('↙',0,2,(-1,-1,0,0)),('DOWN',1,2,(0,-1,0,0)),('↘',2,2,(1,-1,0,0))]
        for text,x,y,axes in positions:jog_button(pad,text,8+x*134,8+y*112,124,104,axes)
        button(pad,'STOP',142,120,124,'stop();',104,'91414b')
        label(ptz,'JOG SPEED',12,451,408,26,size=14);steps(ptz,'speed',1,49,12,482,408)
        label(ptz,'Release / exit stops · 0.9s watchdog',12,537,408,26,colour='a9bbc8',size=13)
        for key,x,top,bottom in [('iris',440,'CLOSE','OPEN'),('zoom',684,'WIDE','TELE'),('focus',928,'NEAR','FAR')]:
            box=card(ptz,x,0,228,560);label(box,SHORT[key],14,10,200,28,size=16);entry(box,key,14,48,200)
            if key=='iris':
                button(box,top,14,108,200,"send('write',{parameter:'iris',value:1365},null);",52)
                button(box,bottom,14,405,200,"send('write',{parameter:'iris',value:4095},null);",52)
            else:
                axes=(0,0,-1,0) if key=='zoom' else (0,0,0,-1)
                jog_button(box,top,14,108,200,52,axes);jog_button(box,bottom,14,405,200,52,tuple(-v for v in axes))
            fader(box,key,42,172,144,221);feedback(box,key,14,465,200)
            if key in ('iris','focus'):
                mode=key+'_auto'
                button(box,'Manual',14,502,96,f"send('write',{{parameter:'{mode}',value:0}},null);",48)
                button(box,'Auto',118,502,96,f"send('write',{{parameter:'{mode}',value:1}},null);",48)
        presets=content['Presets'];label(presets,'CAMERA SHOTS / BANK 01–20',12,0,1162,30,size=17)
        for i in range(20):button(presets,f'{i+1:02d}\nShot {i+1}',12+(i%5)*170,42+(i//5)*126,158,f'preset({i+1});',114,BUTTON,'shot_'+str(i+1))
        side=card(presets,874,42,300,516);label(side,'RECALL / STORE',14,12,272,28,size=17)
        label(side,'0 recall / 1 store',14,49,272);entry(side,'store',14,80,272)
        label(side,'Overwrite confirmation',14,143,272);entry(side,'confirmation',14,176,272,48,None)
        label(side,'Type OVERWRITE before storing.',14,232,272,45,colour='a9bbc8',size=13)
        label(side,'NAME A SHOT',14,288,272);entry(side,'shot_number',14,324,80);entry(side,'shot_name',102,324,184,48,None)
        button(side,'Save shot name',14,388,272,'renamePreset();',52)
        label(side,'Physical recall completion\nrequires camera feedback.',14,454,272,48,colour='a9bbc8',size=13)
        paint=content['Paint']
        for i,key in enumerate(['red_gain','blue_gain','detail']):vertical(paint,key,defs[key],12+i*224,12,208,500)
        for i,key in enumerate(['wb_mode','iris_auto','focus_auto']):
            box=card(paint,700,12+i*164,474,148);label(box,SHORT[key],16,10,442,28,size=17)
            if key=='wb_mode':entry(box,key,16,50,442,56,6)
            else:
                button(box,'Manual',16,50,214,f"send('write',{{parameter:'{key}',value:0}},null);",56)
                button(box,'Auto',244,50,214,f"send('write',{{parameter:'{key}',value:1}},null);",56)
            feedback(box,key,16,114,442)
        label(paint,'White balance values depend on the selected model.',12,528,1162,30,'paint_help',colour='a9bbc8',size=13)
        td=content['TD1C'];label(td,'TOUCHDRIVE / CARBONITE CAMERA BRIDGE',16,12,1154,32,size=19)
        label(td,'Connection not verified',16,60,1154,52,'ross_state')
        for i,text in enumerate(['Physical positioner and native shot commands reach the development simulator.',
                                  'Movement verification is partial; continuous response still needs work.',
                                  'Actual Preset-bus following is pending; the selected target is a lab fixture.',
                                  'Native Custom Control Recall Shot has been observed at the simulator.',
                                  'Real-camera motion and shot completion require separate verification.']):label(td,text,16,132+i*56,1154,44,size=15)
        button(td,'LAB: select on Preset',16,440,330,"labBus('preset');",56,BLUE)
        button(td,'LAB: change Program only',362,440,330,"labBus('program');",56)
        label(td,'Simulator selection only. These buttons do not change the switcher.',16,516,1154,32,colour='a9bbc8',size=13)
    else:
        for page,keys in [('Paint',['red_gain','blue_gain','black_level','gamma']),('Image',['colour','sharpness','brightness','gain'])]:
            for i,key in enumerate(keys):vertical(content[page],key,defs[key],12+i*294,12,276,500)
            label(content[page],'LAB MODEL · CV226/CV228 serial command map awaits camera verification.',12,528,1162,30,colour='d7bb8c',size=13)
        exposure=content['Exposure']
        for i,key in enumerate(['wb_mode','exposure_auto','agc_limit','shutter','dnr','mirror','flip','digital_zoom']):horizontal(exposure,key,defs[key],12+(i%2)*590,12+(i//2)*136,572)
        osd=content['OSD'];label(osd,'OSD / CAMERA SETUP',16,12,1154,32,size=19)
        label(osd,'Fixed cameras · no mechanical pan/tilt',16,56,1154,30,colour='a9bbc8')
        for key,text,x,y in [('menu','MENU',200,112),('up','UP',200,196),('left','LEFT',20,280),('enter','ENTER',200,280),('right','RIGHT',380,280),('down','DOWN',200,364),('back','BACK',200,448)]:button(osd,text,x,y,164,"send('osd',{key:'"+key+"'},function(r){if(r)status(r.status);});",68)
        label(osd,'RS485 adapter / address / firmware',620,156,546,32,size=17)
        label(osd,'Synthetic LAB model.\nNo serial packets are transmitted.\nExact gateway and camera firmware pending.',620,216,546,160,colour='a9bbc8',size=16)
    config=content['Config'];label(config,'CONNECTION / OPERATOR LOGIN',20,12,1140,32,size=19)
    for oid,caption,y,w in [('bridge','Backend',76,780),('username','Username',144,460),('password','Password',212,460)]:
        label(config,caption,20,y+8,160,32,size=17);entry(config,oid,200,y,w,52,None)
    button(config,'Sign in',200,288,218,'login();',56,BLUE)
    button(config,'Sign out',442,288,218,"stop();cbToken='';cbTouchEnabled=false;status('Signed out');",56)
    button(config,'Lock camera',200,368,218,"send('lock',{value:true},null);",56)
    button(config,'Unlock camera',442,368,218,"send('lock',{value:false},null);",56)
    if pana:
        button(config,'Tally ON',700,288,210,"send('tally',{program:true,preview:false},null);",56)
        button(config,'Tally OFF',934,288,210,"send('tally',{program:false,preview:false},null);",56)
        label(config,'Tally feedback pending',700,360,450,88,'tally_state',size=14)
    label(config,'Tally enable / disable, configuration and diagnostics: open CameraBridge setup.',20,454,1140,36,colour='a9bbc8',size=14)
    label(config,'SIMULATOR feedback confirms simulator state. Verify hardware separately.',20,506,1140,36,colour='d7bb8c',size=14)
    label(root,'Starting…',164,744,1186,44,'status','b9c5cf',14)
    path=HERE/f'SW-{manufacturer}-Camera-Control.grid'
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path
