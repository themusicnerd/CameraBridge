"""Native Sony lens, paint and tally panel for the TouchDrive canvas."""
import xml.etree.ElementTree as ET
from build_panels import COMMON,HERE,node,script
from aura_layout import BG,BLUE,BUTTON,card,label,button,entry,jog_button,vertical,horizontal

def build(defs):
    root=ET.Element('abs',{'contexttype':'opengear','id':'_top','name':'CameraBridge Sony','virtualwidth':'1366','virtualheight':'800','width':'1366','height':'800','gridaspect':'false','style':f'bg#{BG};fg#e2e4e9;size:16;'})
    node(root,'api').text="var CB_MANUFACTURER='Sony';\n"+COMMON
    meta=node(root,'meta');params=node(meta,'params')
    for oid,value,widget in [('bridge','http://127.0.0.1:8088',3),('username','',3),('password','',4),('camera','sony1',3)]:
        node(params,'param',oid=oid,name=oid,type='STRING',value=value,widget=widget,access=0 if oid=='camera' else 1,maxlength=256)
    node(params,'param',oid='speed',type='INT32',value=24,access=1,constrainttype='INT_RANGE',constraint='1;49;')
    for key,p in defs.items():
        if key in ('shutter','zoom'):node(params,'param',oid=key,name=p.label,type='STRING',value=str(p.low),access=0,maxlength=32)
        else:node(params,'param',oid=key,name=p.label,type='INT32',value=p.low,access=0,constrainttype='INT_RANGE',constraint=f'{p.low};{min(p.high,2147483647)};')
        n=script(root,"changed('"+key+"');",'onchange');n.set('oid',key);n.set('element','0')
    node(meta,'timer',id='bridge_tick',rate=200,autostart='true');node(meta,'timertask',timerid='bridge_tick',tasktype='ogscript').text='tick();'
    script(root,"highlightPage('Lens');poll();",'onload');script(root,'stop();','onclose')
    header=card(root,8,8,1350,80);label(header,'CameraBridge / Sony',16,12,320,30,size=22);label(header,'PXW-Z200 · lens & paint',16,47,320,24,size=14)
    for i,name in enumerate(['Lens','Paint','Tally','Config']):node(header,'reveal',id='nav_'+name.lower(),name=name,targetid='page_'+name.lower(),left=350+130*i,top=12,width=120,height=56,style=f'bg#{BUTTON};fg#ffffff;size:16;')
    launcher=node(header,'abs',id='bridge_launcher',left=890,top=12,width=180,height=56)
    node(launcher,'help',id='open_bridge',name='Open setup',left=0,top=0,width=180,height=56,title='CameraBridge setup').text='Set the bridge URL on Config.'
    node(header,'image',src=(HERE/'assets/sony.png').as_uri(),left=1150,top=22,width=150,height=29)
    label(root,'Camera identification pending',164,100,1180,28,'identity',size=18);label(root,'Awaiting feedback',164,133,1180,24,'connection',size=14)
    rail=card(root,8,104,140,624);label(rail,'CAMERAS',10,10,120)
    for i in range(6):button(rail,'-',8,42+64*i,124,f'cameraAt({i});',54,id='camera_pick_'+str(i))
    button(rail,'Next',8,438,124,'nextCamera();');button(rail,'Refresh',8,500,124,'poll();');button(rail,'STOP',8,564,124,'stop();',52,'a23d4c')
    tabs=node(root,'tab',left=164,top=164,width=1186,height=564,tabposition='none',onchange='highlightPage(String(this.getTitleAt(this.getSelectedIndex())));')
    pages={name:node(tabs,'abs',id='page_'+name.lower(),name=name,width=1186,height=564,style=f'bg#{BG};') for name in ['Lens','Paint','Tally','Config']}
    lens=pages['Lens'];button(lens,'Touch control DISABLED',12,12,560,'touchEnable();',56,id='touch_enable')
    for y,title,axis,low,high in [(92,'ZOOM',2,'WIDE','TELE'),(270,'FOCUS',3,'NEAR','FAR')]:
        label(lens,title,12,y,560,32,size=20)
        axes=[0,0,0,0];axes[axis]=-1;jog_button(lens,low,12,y+46,265,104,axes);axes[axis]=1;jog_button(lens,high,293,y+46,265,104,axes)
    for i,key in enumerate(['iris','iris_auto','focus_auto']):horizontal(lens,key,defs[key],594,12+170*i,580)
    label(lens,'ZOOM SCALE',12,452,560,22,size=14)
    label(lens,'Awaiting camera',12,478,560,24,'actual_zoom',colour='a9bbc8',size=14)
    label(lens,'Hold / release stops · fixed-speed SDK lens jog · no pan/tilt motors',12,506,560,48,colour='a9bbc8',size=14)
    paint=pages['Paint']
    for i,key in enumerate(['red_gain','blue_gain','colour_temperature']):vertical(paint,key,defs[key],12+i*226,12,212,530)
    for i,key in enumerate(['wb_mode','gain','shutter']):horizontal(paint,key,defs[key],704,12+i*174,470)
    tally=pages['Tally'];label(tally,'CAMERA TALLY',20,16,1140,36,size=22)
    label(tally,'Per-camera enable defaults to ON. Change it in CameraBridge setup.',20,70,1140,36,size=17)
    label(tally,'Awaiting tally feedback',20,136,1140,85,'tally_state',size=17)
    for i,(text,data) in enumerate([('PROGRAM',"{program:true,preview:false}"),('PREVIEW',"{program:false,preview:true}"),('OFF',"{program:false,preview:false}")]):button(tally,text,20+i*380,258,350,"send('tally',"+data+",function(r){if(r)poll();});",80)
    label(tally,'PXW-Z200: external tally lamp control is not listed in Sony SDK 2.02.00.\nUnsupported lamp requests are reported. Recording is never used as tally.',20,390,1130,100,colour='d7bb8c',size=16)
    config=pages['Config']
    for oid,caption,y in [('bridge','Bridge URL',30),('username','Username',110),('password','Password',190)]:label(config,caption,20,y+8,180);entry(config,oid,210,y,760,56,None)
    button(config,'Sign in',210,284,260,'login();',60,BLUE);button(config,'Sign out',490,284,260,"stop();cbToken='';",60)
    label(config,'Set the camera network access and verified SSH fingerprint in CameraBridge setup.',20,386,1140,60,size=17)
    label(config,'Values use Sony native units. Only available camera controls are writable.',20,470,1140,48,colour='a9bbc8',size=15)
    label(root,'Starting…',164,744,1186,44,'status',size=14)
    path=HERE/'SW-Sony-Camera-Control.grid';ET.indent(root);ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True);return path
