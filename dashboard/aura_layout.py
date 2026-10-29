"""Native TD1C touch layout. A 1366x800 canvas leaves room for DashBoard chrome."""
import xml.etree.ElementTree as ET
import json
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
    if widget==6:
        # Use a touch launch surface rather than relying on parameter-widget
        # mouse forwarding, which differs between native DashBoard builds.
        e=node(parent,'button',id='number_entry_'+key,name='...',buttontype='push',left=x,top=y,width=w,height=h,style='bg#1b1e23;fg#ffffff;bdr:line;bdr#383d45;size:18;txt-align:center;')
        task(e,"numberOpen('"+key+"');");return e
    e=field(parent,key,x,y,w,h,widget);e.set('style','size:18;txt-align:center;');return e


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
    entry(box,key,16,50,w-32);label(box,'Range '+str(p.low)+' to '+str(p.high),16,100,w-32,22,'range_'+key,size=12);fader(box,key,32,134,w-64,h-246)
    button(box,'−',16,h-100,80,f"adjust('{key}',-1,{p.low},{p.high});",52)
    button(box,'+',w-96,h-100,80,f"adjust('{key}',1,{p.low},{p.high});",52)
    feedback(box,key,16,h-38,w-32);return box

def horizontal(parent,key,p,x,y,w=572):
    box=card(parent,x,y,w,122);label(box,SHORT[key],16,8,w-240,26,size=16);label(box,'Range '+str(p.low)+' to '+str(p.high),w-218,8,202,26,'range_'+key,size=12)
    steps(box,key,p.low,p.high,16,39,w-32);feedback(box,key,16,90,w-32);return box

def jog_button(parent,text,x,y,w,h,axes,root=None):
    ident='jog_'+('_'.join(str(a).replace('-','minus') for a in axes))
    b=node(parent,'button',id=ident,name=text,buttontype='push',left=x,top=y,width=w,height=h,style='bg#202328;fg#e2e4e9;bdr:line;bdr#383d45;size:22;')
    target=root if root is not None else b
    for event,code in [('onmousedown','jog('+','.join(map(str,axes))+');'),('onmouseup','release();'),('onmouseexit','release();')]:
        script(target,code,event).set('targetid',ident)
    return b

def build(manufacturer,defs):
    pana=manufacturer=='Panasonic'
    root=ET.Element('abs',{'contexttype':'opengear','id':'_top','name':'CameraBridge '+manufacturer,
        'virtualwidth':'1366','virtualheight':'800','width':'1366','height':'800','gridaspect':'false','gridsize':'10',
        'keepalive':'false','style':f'bg#{BG};fg#e2e4e9;size:16;'})
    node(root,'api').text=f"var CB_MANUFACTURER = '{manufacturer}';\n"+COMMON
    meta=node(root,'meta');params=node(meta,'params')
    if pana:
        for high in (1,2):node(meta,'constraint',id='detail_range_'+str(high),constrainttype='INT_RANGE',constraint=f'0;{high};')
        for step in (1,5):node(meta,'constraint',id='gain_range_'+str(step),constrainttype='INT_RANGE',constraint=f'0;300;{-150//step};{150//step};')
        node(meta,'constraint',id='gain_range_hc1800',constrainttype='INT_RANGE',constraint='0;300;-90;90;')
    for oid,name,value,widget,access in [('bridge','Backend URL','http://127.0.0.1:8088',3,1),('username','Username','',3,1),('password','Password','',4,1),('camera','Camera ID','pana1' if pana else 'marshall1',3,0),('confirmation','Type OVERWRITE','',3,1),('shot_name','Shot name','',3,1)]:
        node(params,'param',oid=oid,name=name,type='STRING',value=value,widget=widget,access=access,maxlength=256)
    for oid,name,low,high,value in [('speed','Jog speed',1,49,12),('store','Store armed',0,1,0),('shot_number','Shot number',1,100,1),('recall_speed','Recall Speed',1,30,15),('use_saved_speed','Use Saved Speed',0,1,1)]:
        n=node(params,'param',oid=oid,name=name,type='INT32',value=value,access=1,constrainttype='INT_RANGE',constraint=f'{low};{high};')
        if oid in ('store','use_saved_speed'):
            n.set('constrainttype','INT_CHOICE');n.attrib.pop('constraint')
            for v,caption in enumerate(('Recall','Store') if oid=='store' else ('Override','Saved')):node(n,'constraint',key=v).text=caption
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
    label(header,'PTZ and Camera Control' if pana else 'CV226 / CV228 · paint & setup',16,45,325,24,colour='abb1bd',size=14)
    pages=['PTZ','Presets','Paint','Config'] if pana else ['Paint','Image','Exposure','OSD','Config']
    for i,name in enumerate(pages):node(header,'reveal',id='nav_'+name.lower(),name='TouchDrive' if name=='TD1C' else name,targetid='page_'+name.lower(),left=350+i*(144 if pana else 112),top=12,width=132 if pana else 104,height=56,style=f'bg#{PURPLE if i==0 else BUTTON};fg#ffffff;bdr:none;size:16;')
    launcher=node(header,'abs',id='bridge_launcher',left=920,top=12,width=180,height=56)
    help_button=node(launcher,'help',id='open_bridge',left=0,top=0,width=180,height=56,name='Open setup',title='CameraBridge setup',popupwidth=600,popupheight=180,style=f'bg#{BLUE};fg#ffffff;size:16;')
    help_button.text='<html>Set the backend URL on Config. Select Open CameraBridge again after feedback loads.</html>' 
    logo_width=164 if pana else 177
    node(header,'image',src=(HERE/'assets'/('panasonic.png' if pana else 'marshall.png')).as_uri(),left=1328-logo_width,top=15,width=logo_width,height=48)
    label(root,'Camera identification pending',164,100,1178,26,'identity',size=18)
    label(root,'Connecting',164,130,1178,24,'connection','a9bbc8',14)
    rail=card(root,8,104,140,624);label(rail,'CAMERAS',10,10,120,26,size=14)
    for i in range(6):button(rail,'-',8,42+i*64,124,f'cameraAt({i});',54,PURPLE if i==0 else BUTTON,'camera_pick_'+str(i))
    button(rail,'Next',8,432,124,'nextCamera();',48);button(rail,'Refresh',8,492,124,'poll();',48)
    button(rail,'STOP',8,552,124,'stop();',64,'a23d4c')
    tabs=node(root,'tab',left=164,top=164,width=1186,height=564,tabposition='none',delay='false',onchange='highlightPage(String(this.getTitleAt(this.getSelectedIndex())));')
    content={name:node(tabs,'abs',id='page_'+name.lower(),name=name,width=1186,height=564,style=f'bg#{BG};') for name in pages}
    if pana:
        ptz=content['PTZ'];label(ptz,'PAN / TILT CONTROL',12,0,408,28,size=17)
        button(ptz,'Touch control DISABLED',12,36,408,'touchEnable();',48,BUTTON,'touch_enable')
        pad=card(ptz,12,96,408,344)
        positions=[('↖',0,0,(-1,1,0,0)),('UP',1,0,(0,1,0,0)),('↗',2,0,(1,1,0,0)),('LEFT',0,1,(-1,0,0,0)),('RIGHT',2,1,(1,0,0,0)),('↙',0,2,(-1,-1,0,0)),('DOWN',1,2,(0,-1,0,0)),('↘',2,2,(1,-1,0,0))]
        for text,x,y,axes in positions:jog_button(pad,text,8+x*134,8+y*112,124,104,axes,root)
        button(pad,'STOP',142,120,124,'stop();',104,'91414b')
        label(ptz,'JOG SPEED | RANGE 1 TO 49',12,451,408,26,size=14);steps(ptz,'speed',1,49,12,482,408)
        label(ptz,'Release / exit stops · 0.9s watchdog',12,537,408,26,colour='a9bbc8',size=13)
        for key,x,top,bottom in [('iris',440,'OPEN','CLOSE'),('zoom',684,'TELE','WIDE'),('focus',928,'FAR','NEAR')]:
            box=card(ptz,x,0,228,560);label(box,SHORT[key],14,10,200,28,size=16);entry(box,key,14,48,200)
            if key=='iris':
                button(box,top,14,126,200,"send('write',{parameter:'iris',value:4095},null);",52)
                button(box,bottom,14,405,200,"send('write',{parameter:'iris',value:1365},null);",52)
            else:
                axes=(0,0,1,0) if key=='zoom' else (0,0,0,1)
                jog_button(box,top,14,126,200,52,axes,root);jog_button(box,bottom,14,405,200,52,tuple(-v for v in axes),root)
            label(box,'Range '+str(defs[key].low)+' to '+str(defs[key].high),14,99,200,22,'range_'+key,size=12);fader(box,key,42,192,144,201);feedback(box,key,14,465,200)
            if key in ('iris','focus'):
                mode=key+'_auto'
                button(box,'Manual',14,502,96,f"send('write',{{parameter:'{mode}',value:0}},null);",48)
                button(box,'Auto',118,502,96,f"send('write',{{parameter:'{mode}',value:1}},null);",48)
        presets=content['Presets'];label(presets,'CAMERA SHOTS / BANK 01–20',12,0,1162,30,size=17)
        for i in range(20):button(presets,f'{i+1:02d}\nShot {i+1}',12+(i%5)*170,42+(i//5)*126,158,f'preset({i+1});',114,BUTTON,'shot_'+str(i+1))
        side=card(presets,874,42,300,516);label(side,'RECALL / STORE',14,12,272,28,size=17)
        label(side,'Action',14,43,272);entry(side,'store',14,70,272,48,7)
        label(side,'Type OVERWRITE to Store',14,114,272);entry(side,'confirmation',14,142,272,48,None)
        label(side,'Recall Speed: 1 Slow / 30 Fast',14,188,272,24,size=13);entry(side,'recall_speed',14,214,272,48)
        label(side,'Recall Speed Mode',14,260,272,24,size=13);entry(side,'use_saved_speed',14,286,272,48,7)
        label(side,'Shot Number (1 to 100) / Name',14,332,272,24,'shot_number_label',size=12);entry(side,'shot_number',14,358,70,48);entry(side,'shot_name',92,358,194,48,None)
        button(side,'Save Name and Speed',14,406,272,'renamePreset();',48)
        label(side,'No Shot Recalled',14,460,272,48,'preset_feedback',colour='a9bbc8',size=12)
        paint=content['Paint']
        for i,key in enumerate(['red_gain','blue_gain','detail']):vertical(paint,key,defs[key],12+i*224,12,208,500)
        wb=card(paint,700,12,474,366);label(wb,'WHITE BALANCE',16,10,442,28,size=17)
        button(wb,'Auto ATW',16,48,138,'whiteBalance(0);',48)
        button(wb,'Manual A',164,48,138,'whiteBalance(2);',48)
        button(wb,'Manual B',312,48,146,'whiteBalance(3);',48)
        button(wb,'One Shot',16,106,214,'oneShot();',48)
        button(wb,'VAR / Kelvin',244,106,214,'whiteBalance(9);',48)
        feedback(wb,'wb_mode',16,160,442)
        label(wb,'Colour Temperature (K)',16,194,442,24,size=15)
        entry(wb,'colour_temperature',16,222,442,48)
        label(wb,'Range 2000 to 15000 K',16,274,442,22,'range_colour_temperature',size=12)
        feedback(wb,'colour_temperature',16,296,442)
        label(wb,'One Shot: Not Requested',16,332,442,26,'awb_result',size=12)
        for i,key in enumerate(['iris_auto','focus_auto']):
            box=card(paint,700+i*244,390,230,116);label(box,SHORT[key],12,4,206,26,size=16)
            button(box,'Manual',12,34,98,f"send('write',{{parameter:'{key}',value:0}},null);",48)
            button(box,'Auto',120,34,98,f"send('write',{{parameter:'{key}',value:1}},null);",48)
            feedback(box,key,12,84,206)
        label(paint,'White balance values depend on the selected model.',12,528,1162,30,'paint_help',colour='a9bbc8',size=13)

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
    label(config,'CameraBridge Connection Settings',20,506,1140,36,colour='d7bb8c',size=14)
    label(root,'Starting…',164,744,1186,44,'status','b9c5cf',14)
    from numeric_entry import build as build_numeric
    build_numeric(root,params)
    numbers={e.get('id')[13:]:True for e in root.iter() if (e.get('id') or '').startswith('number_entry_')}
    ranges={e.get('id')[6:]:True for e in root.findall('.//label') if (e.get('id') or '').startswith('range_')}
    root.find('api').text+='\ncbNumberFields='+json.dumps(numbers)+';cbRangeFields='+json.dumps(ranges)+';'
    path=HERE/f'SW-{manufacturer}-Camera-Control.grid'
    ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return path
