let REC_STATE = { selectedImages: [] };

function setNow(inputEl){ if(!inputEl) return; try{ const d=new Date(); inputEl.value = new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16); }catch{} }

async function fetchJSON(url, opts){
  const timeoutMs = (window.APP_CFG && Number(window.APP_CFG.apiTimeoutMs)) || 30000;
  const ctrl = new AbortController();
  const t = setTimeout(()=> ctrl.abort(), timeoutMs);
  try{
    const r = await fetch(url, Object.assign({ signal: ctrl.signal }, opts||{}));
    let data = {}; try{ data = await r.json(); }catch{}
    return { ok: r.ok, data, status: r.status };
  }catch(e){
    return { ok: false, data: { error: (e && e.name==='AbortError')? 'timeout' : String(e) }, status: 0 };
  } finally {
    clearTimeout(t);
  }
}

function closeRecordModal(){
  const modal = document.getElementById('recordModal');
  if(modal) modal.style.display='none';
}

function resetRecordForm(){
  const form = document.getElementById('recordForm');
  if(!form) return;
  form.reset();
  REC_STATE.selectedImages = [];
  const list = document.getElementById('selectedImagesList'); if(list) list.innerHTML='';
  const block = document.getElementById('selectedImagesBlock'); if(block) block.style.display='none';
  const imgs = document.getElementById('recordImgs'); if(imgs) imgs.innerHTML='';
  const addBtn = document.getElementById('recordAddImgBtn'); if(addBtn) addBtn.style.display='none';
  const json = document.getElementById('selectedImagesJson'); if(json) json.value='[]';
}

function openRecordModal(profileId, path, line){
  resetRecordForm();
  const modal = document.getElementById('recordModal');
  const form = document.getElementById('recordForm');
  form.elements['profile_id'].value = profileId;
  form.elements['file_path'].value = path||'';
  const view = document.getElementById('recordLineView'); if(view) view.value = line||'';
  setNow(form.elements['event_dt']);
  modal.style.display='flex';
}

function openImageRecordModal(profileId, imagePath){
  resetRecordForm();
  const modal = document.getElementById('recordModal');
  const form = document.getElementById('recordForm');
  form.elements['profile_id'].value = profileId;
  form.elements['file_path'].value = imagePath||'';
  const view = document.getElementById('recordLineView'); if(view) view.value = '';
  const block = document.getElementById('selectedImagesBlock');
  const list = document.getElementById('selectedImagesList');
  if(block) block.style.display='block';
  if(list){
    const t = document.createElement('div'); t.className='thumb';
    const im = document.createElement('img'); im.src = `/api/profiles/${profileId}/image?path=${encodeURIComponent(imagePath)}`; t.appendChild(im);
    const meta = document.createElement('div'); meta.className='meta';
    const si = document.createElement('span'); si.className='idx'; si.textContent = '#1'; meta.appendChild(si);
    const vb = document.createElement('button'); vb.type='button'; vb.textContent='View'; vb.onclick=()=>{ openImageViewer([im.src],0); }; meta.appendChild(vb);
    t.appendChild(meta); list.appendChild(t);
  }
  REC_STATE.selectedImages = [imagePath];
  const json = document.getElementById('selectedImagesJson'); if(json) json.value = JSON.stringify(REC_STATE.selectedImages);
  setNow(form.elements['event_dt']);
  modal.style.display='flex';
}

function openRecordDetail(rec){
  resetRecordForm();
  const modal = document.getElementById('recordModal');
  const form = document.getElementById('recordForm');
  form.elements['id'].value = rec.id;
  form.elements['profile_id'].value = rec.profile_id||'';
  form.elements['file_path'].value = rec.file_path||'';
  form.elements['title'].value = rec.title||'';
  form.elements['situation'].value = rec.situation||'';
  form.elements['description'].value = rec.description||'';
  const view = document.getElementById('recordLineView'); if(view) view.value = rec.content||'';
  if(rec.event_time){ const dt = new Date(rec.event_time*1000); form.elements['event_dt'].value = new Date(dt.getTime()-dt.getTimezoneOffset()*60000).toISOString().slice(0,16); }
  const grid = document.getElementById('recordImgs');
  const addBtn = document.getElementById('recordAddImgBtn'); if(addBtn) addBtn.style.display='inline-block';
  if(grid){
    (rec.images||[]).forEach(img=>{
      const wrap = document.createElement('div'); wrap.className='thumb';
      wrap.innerHTML = `<img src="${img.url||img.path}" loading="lazy"><div class="meta"><span class="idx">#${img.id}</span><button type="button" data-act="imgview" data-src="${img.url||img.path}">View</button><button type="button" data-act="imgdel" data-id="${img.id}" style="border-color:#991b1b">Remove</button></div>`;
      grid.appendChild(wrap);
    });
  }
  modal.style.display='flex';
}

document.addEventListener('DOMContentLoaded', ()=>{
  const form = document.getElementById('recordForm');
  const cancelBtns = document.querySelectorAll('.record-close');
  cancelBtns.forEach(btn=> btn.addEventListener('click', closeRecordModal));
  if(form){
    form.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const fd = new FormData(form);
      const payload = {
        profile_id: Number(fd.get('profile_id')||0),
        title: String(fd.get('title')||''),
        file_path: String(fd.get('file_path')||''),
        filter: '',
        content: String(fd.get('content')||''),
        situation: String(fd.get('situation')||''),
        event_time: (function(){ const dt = fd.get('event_dt'); if(!dt) return null; const t = Date.parse(dt); return isNaN(t)? null : Math.floor(t/1000); })(),
        description: String(fd.get('description')||''),
      };
      const rid = fd.get('id');
      let rec = null;
      if(rid){
        const r = await fetch(`/api/records/${rid}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if(!r.ok){ alert('Save failed'); return; }
        rec = await r.json();
      } else {
        const r = await fetch('/api/records', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if(!r.ok){ alert('Failed to save record'); return; }
        rec = await r.json();
        try{
          const imgsSel = JSON.parse(document.getElementById('selectedImagesJson').value||'[]');
          for(const rp of imgsSel){
            await fetch(`/api/records/${rec.id}/image_remote`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ profile_id: payload.profile_id, path: rp }) });
          }
        }catch{}
        const files = (document.querySelector('#recordForm input[name="images"]').files)||[];
        for(const f of files){ const fdf = new FormData(); fdf.append('file', f); await fetch(`/api/records/${rec.id}/image`, { method:'POST', body: fdf }); }
      }
      closeRecordModal();
      window.dispatchEvent(new CustomEvent('recordSaved', {detail: rec}));
      alert('Record saved');
    });
  }
  const imgGrid = document.getElementById('recordImgs');
  if(imgGrid){
    imgGrid.addEventListener('click', async (e)=>{
      const btn = e.target.closest('button'); if(!btn) return;
      if(btn.dataset.act==='imgview'){
        const urls = [...imgGrid.querySelectorAll('img')].map(im=> im.getAttribute('src'));
        const src = btn.dataset.src; const idx = urls.indexOf(src);
        openImageViewer(urls, idx>=0?idx:0);
        return;
      }
      if(btn.dataset.act==='imgdel'){
        const iid = btn.dataset.id; const r = await fetch(`/api/record_images/${iid}`, { method:'DELETE' });
        if(r.ok){ closeRecordModal(); window.dispatchEvent(new CustomEvent('recordSaved', {})); }
      }
    });
  }
  const addBtn = document.getElementById('recordAddImgBtn');
  if(addBtn){
    addBtn.addEventListener('click', async ()=>{
      const rid = document.getElementById('recordForm').elements['id'].value;
      const files = document.getElementById('recordAddImg').files||[];
      if(!files.length) return;
      for(const f of files){ const fd = new FormData(); fd.append('file', f); await fetch(`/api/records/${rid}/image`, { method:'POST', body: fd }); }
      alert('Images added');
      closeRecordModal();
      window.dispatchEvent(new CustomEvent('recordSaved', {detail:{id:rid}}));
    });
  }
});
