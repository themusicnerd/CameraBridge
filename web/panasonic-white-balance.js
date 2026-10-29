function cameraWhiteBalanceControls(camera) {
    const section=document.createElement('div');section.className='white-balance-controls';
    section.hidden=camera.driver!=='panasonic';
    section.innerHTML='<h3>White Balance</h3><div class="fields"><label>White Balance Mode<select data-wb-mode disabled></select></label><label>Colour Temperature (K)<input data-wb-kelvin type="number" inputmode="numeric" step="10" disabled></label><p class="feedback wide" data-wb-feedback role="status">Waiting For Camera Feedback</p></div><p class="hint" data-wb-hint>Select VAR To Set Kelvin. The Camera Uses Its Nearest Supported Value.</p>';
    async function write(parameter,value){
        const feedback=section.querySelector('[data-wb-feedback]');
        try {
            await api('command',{camera:camera.id,action:'write',data:{parameter,value}});
            feedback.textContent='Sent; Waiting For Camera Readback';
        } catch(error) {feedback.textContent=error.message;}
    }
    section.querySelector('[data-wb-mode]').onchange=event=>write('wb_mode',Number(event.target.value));
    section.querySelector('[data-wb-kelvin]').onchange=event=>{
        if(event.target.checkValidity())write('colour_temperature',Number(event.target.value));
        else event.target.reportValidity();
    };
    return section;
}

function refreshCameraWhiteBalance(row,camera) {
    const section=row.querySelector('.white-balance-controls');if(!section)return;
    section.hidden=camera.driver!=='panasonic';if(section.hidden)return;
    const mode=camera.parameters?.wb_mode,kelvin=camera.parameters?.colour_temperature;
    const select=section.querySelector('[data-wb-mode]'),input=section.querySelector('[data-wb-kelvin]');
    const names=camera.model==='AW-HE2'?{0:'Auto ATW',1:'Manual A',2:'Manual B',3:'Auto ATW',4:'3200 K',5:'5600 K',6:'4500 K',7:'6000 K',8:'2800 K'}:{0:'Auto ATW',2:'Manual A',3:'Manual B',4:'3200 K',5:'5600 K',9:'VAR / Kelvin'};
    const choices=mode?.allowed||[],signature=choices.join(',');
    if(select.dataset.choices!==signature){
        select.replaceChildren(...choices.map(value=>{const option=document.createElement('option');option.value=value;option.textContent=names[value]||String(value);return option}));
        select.dataset.choices=signature;
    }
    const active=!!role&&!camera.locked&&['online','simulated'].includes(camera.health);
    select.disabled=!(active&&mode?.writable&&mode.confirmation==='confirmed');
    if(document.activeElement!==select&&mode?.value!=null)select.value=mode.value;
    input.min=kelvin?.low||2000;input.max=kelvin?.high||15000;
    input.disabled=!(active&&kelvin?.supported&&kelvin.writable&&kelvin.confirmation==='confirmed'&&mode?.confirmation==='confirmed'&&mode.value===9&&(mode.age_seconds??Infinity)<10);
    if(document.activeElement!==input&&kelvin?.value!=null)input.value=kelvin.value;
    section.querySelector('[data-wb-feedback]').textContent='Mode: '+(names[mode?.value]||'Unknown')+' | '+(kelvin?.supported?(kelvin.value??'Unknown')+' K | '+kelvin.confirmation:'Kelvin Control Unavailable On This Model');
    section.querySelector('[data-wb-hint]').textContent=kelvin?.supported?'Select VAR To Set '+input.min+' To '+input.max+' K. The Camera Uses Its Nearest Supported Value.':'Use The White Balance Modes Supported By This Camera.';
}
