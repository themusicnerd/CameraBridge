function updateOrderButtons(ready) {
    for(let index=0;index<(draft?.cameras.length||0);index++) {
        const row=document.getElementById('camera-'+draft.cameras[index].id);if(!row)continue;
        const up=row.querySelector('[data-order="-1"]'),down=row.querySelector('[data-order="1"]');
        if(up)up.disabled=!ready||index===0;
        if(down)down.disabled=!ready||index===draft.cameras.length-1;
    }
}

function moveCamera(cameraId,direction) {
    if(role!=='admin'||!draft||![-1,1].includes(direction))return;
    const index=draft.cameras.findIndex(camera=>camera.id===cameraId),next=index+direction;
    if(index<0||next<0||next>=draft.cameras.length)return;
    const row=document.getElementById('camera-'+cameraId),other=document.getElementById('camera-'+draft.cameras[next].id);
    [draft.cameras[index],draft.cameras[next]]=[draft.cameras[next],draft.cameras[index]];
    if(direction<0)row.parentNode.insertBefore(row,other);else row.parentNode.insertBefore(other,row);
    updateOrderButtons(true);changed();
    row.querySelector('[data-order="'+direction+'"]').focus();
    row.scrollIntoView({block:'nearest'});
}

function cameraOrderButtons(camera) {
    const controls=document.createElement('span');controls.className='camera-order';
    for(const [direction,arrow,name] of [[-1,'↑','Move Camera Up'],[1,'↓','Move Camera Down']]) {
        const button=document.createElement('button');button.type='button';button.className='reorder-camera';
        button.dataset.order=direction;button.textContent=arrow;button.title=name;button.setAttribute('aria-label',name);
        button.onclick=event=>{event.preventDefault();event.stopPropagation();moveCamera(camera.id,direction)};
        controls.append(button);
    }
    return controls;
}
