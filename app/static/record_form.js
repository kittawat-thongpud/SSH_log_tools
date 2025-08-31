const RECORD_FORM_STATE = { selectedImages: [], selectedTags: [] };
// Use var and reuse existing global to avoid redeclaration errors when this
// script is loaded on multiple pages.
var TAG_CACHE = window.TAG_CACHE || [];
window.TAG_CACHE = TAG_CACHE;
async function loadTagCache(){
  try{
    const r = await fetch('/api/tags');
    const d = await r.json();
    TAG_CACHE = d.tags||[];
  }catch{ TAG_CACHE = []; }
  return TAG_CACHE;
}
window.loadTagCache = loadTagCache;
function setNow(inputEl){ if(!inputEl) return; try{ const d=new Date(); inputEl.value = new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16); }catch{} }
function renderTagButtons(selected){
  const wrap = document.getElementById('tagList');
  if(!wrap) return;
  wrap.innerHTML='';
  RECORD_FORM_STATE.selectedTags = Array.isArray(selected)? [...selected] : [];
  TAG_CACHE.forEach(t=>{
    const btn=document.createElement('button');
    btn.type='button'; btn.className='tag-btn'; btn.textContent=t.name;
    if(RECORD_FORM_STATE.selectedTags.includes(t.id)) btn.classList.add('selected');
    btn.onclick=()=>{
      const idx=RECORD_FORM_STATE.selectedTags.indexOf(t.id);
      if(idx>=0){ RECORD_FORM_STATE.selectedTags.splice(idx,1); btn.classList.remove('selected'); }
      else { RECORD_FORM_STATE.selectedTags.push(t.id); btn.classList.add('selected'); }
      document.getElementById('recordTagsJson').value = JSON.stringify(RECORD_FORM_STATE.selectedTags);
    };
    wrap.appendChild(btn);
  });
  document.getElementById('recordTagsJson').value = JSON.stringify(RECORD_FORM_STATE.selectedTags);
}
function openRecordForm(opts){
  const modal = document.getElementById('recordModal');
  const form = document.getElementById('recordForm');
  if(!modal || !form) return;
  form.reset();
  const data = opts||{};
  form.elements['id'].value = data.id||'';
  form.elements['profile_id'].value = data.profile_id||'';
  form.elements['file_path'].value = data.file_path||'';
  form.elements['title'].value = data.title||'';
  form.elements['content'].value = data.content||'';
  form.elements['situation'].value = data.situation||'';
  form.elements['description'].value = data.description||'';
  if(data.event_time){ const dt=new Date(data.event_time*1000); form.elements['event_dt'].value = new Date(dt.getTime()-dt.getTimezoneOffset()*60000).toISOString().slice(0,16); }
  else { setNow(form.elements['event_dt']); }
  const titleEl = document.getElementById('recordModalTitle');
  if(titleEl) titleEl.textContent = data.id? 'Record Detail' : 'Save Record';
  loadTagCache().then(()=>{ renderTagButtons((data.tags||[]).map(t=>t.id)); });
  const block = document.getElementById('selectedImagesBlock');
  const list = document.getElementById('selectedImagesList');
  list.innerHTML='';
  RECORD_FORM_STATE.selectedImages = data.selectedImages||[];
  if(data.images && data.images.length){
    block.style.display='block';
    data.images.forEach((img, idx)=>{
      const t=document.createElement('div'); t.className='thumb';
      const im=document.createElement('img'); im.src=img.url||img.path; t.appendChild(im);
      const m=document.createElement('div'); m.className='meta';
      const si=document.createElement('span'); si.className='idx'; si.textContent=img.id? `#${img.id}` : `#${idx+1}`; m.appendChild(si);
      const vb=document.createElement('button'); vb.type='button'; vb.textContent='View'; vb.dataset.src=im.src; m.appendChild(vb);
      if(img.id){ const rb=document.createElement('button'); rb.type='button'; rb.textContent='Remove'; rb.dataset.id=img.id; rb.style.borderColor='#991b1b'; m.appendChild(rb); }
      t.appendChild(m); list.appendChild(t);
    });
  } else { block.style.display='none'; }
  document.getElementById('selectedImagesJson').value = JSON.stringify(RECORD_FORM_STATE.selectedImages);
  modal.style.display='flex';
}
function closeRecordForm(){ const modal=document.getElementById('recordModal'); if(modal) modal.style.display='none'; }
document.addEventListener('DOMContentLoaded', ()=>{
  const form=document.getElementById('recordForm');
  const cancel=document.getElementById('recordCancel');
  if(cancel) cancel.onclick=closeRecordForm;
  if(form){
    form.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const fd=new FormData(form);
      const id=fd.get('id');
      const payload={
        profile_id:Number(fd.get('profile_id')||0),
        title:String(fd.get('title')||''),
        file_path:String(fd.get('file_path')||''),
        filter:'',
        content:String(fd.get('content')||''),
        situation:String(fd.get('situation')||''),
        event_time:(function(){ const dt=fd.get('event_dt'); if(!dt) return null; const t=Date.parse(dt); return isNaN(t)? null: Math.floor(t/1000); })(),
        description:String(fd.get('description')||''),
        tags:(function(){ try{ return JSON.parse(fd.get('tags_json')||'[]'); }catch{ return []; } })()
      };
      let rec=null;
      if(id){
        const r=await fetch(`/api/records/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if(!r.ok){ alert('Save failed'); return; }
        try{ rec=await r.json(); }catch{ rec={id}; }
      } else {
        const r=await fetch('/api/records', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if(!r.ok){ alert('Failed to save record'); return; }
        rec=await r.json();
        try{
          const imgsSel=JSON.parse(document.getElementById('selectedImagesJson').value||'[]');
          for(const rp of imgsSel){
            await fetch(`/api/records/${rec.id}/image_remote`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ profile_id: payload.profile_id, path: rp }) });
          }
        }catch{}
      }
      const files=(form.querySelector('input[name="images"]').files)||[];
      for(const f of files){ const fdf=new FormData(); fdf.append('file', f); await fetch(`/api/records/${rec.id}/image`, { method:'POST', body:fdf }); }
      closeRecordForm();
      document.dispatchEvent(new CustomEvent('recordFormSaved', { detail: rec }));
      alert('Record saved');
    });
    const fileInput=form.querySelector('input[name="images"]');
    if(fileInput){ fileInput.addEventListener('change', ()=>{
      const list=document.getElementById('selectedImagesList');
      const block=document.getElementById('selectedImagesBlock');
      block.style.display='block';
      for(const f of (fileInput.files||[])){
        try{ const url=URL.createObjectURL(f); const t=document.createElement('div'); t.className='thumb'; const im=document.createElement('img'); im.src=url; t.appendChild(im); const m=document.createElement('div'); m.className='meta'; const s=document.createElement('span'); s.className='idx'; s.textContent=f.name; m.appendChild(s); const b=document.createElement('button'); b.type='button'; b.textContent='View'; b.onclick=()=>{ const imgs=Array.from(document.querySelectorAll('#selectedImagesList img')); const arr=imgs.map(el=>el.src); const pos=arr.indexOf(url); if(window.openImageViewer) openImageViewer(arr, pos>=0?pos:0); }; m.appendChild(b); t.appendChild(m); list.appendChild(t); }catch{}
      }
    }); }
    document.getElementById('selectedImagesList').addEventListener('click', async (e)=>{
      const btn=e.target.closest('button'); if(!btn) return;
      if(btn.textContent==='View' && window.openImageViewer){
        const imgs=Array.from(document.querySelectorAll('#selectedImagesList img')).map(el=>el.src);
        const src=btn.dataset.src||btn.parentElement.previousSibling.src;
        const idx=imgs.indexOf(src);
        openImageViewer(imgs, idx>=0?idx:0);
      }
      if(btn.textContent==='Remove' && btn.dataset.id){
        const iid=btn.dataset.id; const r=await fetch(`/api/record_images/${iid}`, { method:'DELETE' });
        if(r.ok){ btn.closest('.thumb').remove(); }
      }
    });
  }
  loadTagCache();
});
function openRecordModal(profileId, path, line){
  openRecordForm({ profile_id: profileId, file_path: path, content: line });
}
function openImageRecordModal(profileId, imagePath){
  openRecordForm({ profile_id: profileId, file_path: imagePath, images:[{path:`/api/profiles/${profileId}/image?path=${encodeURIComponent(imagePath)}`}], selectedImages:[imagePath] });
}
function closeRecordModal(){ closeRecordForm(); }
