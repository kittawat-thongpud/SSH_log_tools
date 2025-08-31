// Reusable Record Form modal widget
const RECORD_STATE = { selectedImages: [] };

function setNow(inputEl){ if(!inputEl) return; try{ const d=new Date(); inputEl.value=new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}catch{} }
function escapeHtml(s){ return String(s||'').replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

function resetRecordForm(){
  const form=document.getElementById('recordForm'); if(!form) return;
  form.reset();
  RECORD_STATE.selectedImages=[];
  const list=document.getElementById('selectedImagesList'); if(list) list.innerHTML='';
  const block=document.getElementById('selectedImagesBlock'); if(block) block.style.display='none';
  document.getElementById('selectedImagesJson').value='[]';
}

function openRecordModal(profileId, path, line){
  resetRecordForm();
  const form=document.getElementById('recordForm');
  form.profile_id.value=profileId;
  const pathInput=form.querySelector('input[name="file_path"]'); if(pathInput) pathInput.value=path||'';
  const view=document.getElementById('recordLineView'); if(view){ view.value=line||''; view.parentElement.style.display='block'; }
  setNow(form.querySelector('input[name="event_dt"]'));
  document.getElementById('recordModal').style.display='flex';
}

function openImageRecordModal(profileId, imagePath){
  resetRecordForm();
  const form=document.getElementById('recordForm');
  form.profile_id.value=profileId;
  const pathInput=form.querySelector('input[name="file_path"]'); if(pathInput) pathInput.value=imagePath||'';
  const view=document.getElementById('recordLineView'); if(view){ view.value=''; view.parentElement.style.display='block'; }
  const block=document.getElementById('selectedImagesBlock'); const list=document.getElementById('selectedImagesList');
  const url=`/api/profiles/${profileId}/image?path=${encodeURIComponent(imagePath)}`;
  const t=document.createElement('div'); t.className='thumb';
  const im=document.createElement('img'); im.src=url; t.appendChild(im);
  const meta=document.createElement('div'); meta.className='meta';
  const name=document.createElement('div'); name.className='name'; name.textContent=imagePath.split(/[\\/]/).pop(); meta.appendChild(name);
  const btnWrap=document.createElement('div'); btnWrap.className='buttons';
  const vb=document.createElement('button'); vb.type='button'; vb.textContent='View'; vb.dataset.act='imgview'; vb.dataset.src=url; btnWrap.appendChild(vb);
  meta.appendChild(btnWrap);
  t.appendChild(meta); list.appendChild(t);
  block.style.display='block';
  RECORD_STATE.selectedImages=[imagePath];
  document.getElementById('selectedImagesJson').value=JSON.stringify(RECORD_STATE.selectedImages);
  setNow(form.querySelector('input[name="event_dt"]'));
  document.getElementById('recordModal').style.display='flex';
}

function openRecordDetail(rec){
  resetRecordForm();
  const form=document.getElementById('recordForm');
  form.elements['id'].value=rec.id||'';
  form.profile_id.value=rec.profile_id||'';
  form.elements['file_path'].value=rec.file_path||'';
  form.elements['title'].value=rec.title||'';
  form.elements['situation'].value=rec.situation||'';
  form.elements['description'].value=rec.description||'';
  form.elements['content'].value=rec.content||'';
  if(rec.event_time){ const dt=new Date(rec.event_time*1000); form.elements['event_dt'].value=new Date(dt.getTime()-dt.getTimezoneOffset()*60000).toISOString().slice(0,16); }
  const list=document.getElementById('selectedImagesList');
  const block=document.getElementById('selectedImagesBlock');
  if(rec.images && rec.images.length){
    rec.images.forEach((img,idx)=>{
      const t=document.createElement('div'); t.className='thumb';
      const im=document.createElement('img'); im.src=img.url||img.path; t.appendChild(im);
      const meta=document.createElement('div'); meta.className='meta';
      const name=document.createElement('div'); name.className='name';
      try{ name.textContent=(img.name||img.path||img.url||'').split(/[\\/]/).pop()||('image'+(idx+1)); }catch{ name.textContent='image'+(idx+1); }
      meta.appendChild(name);
      const btnWrap=document.createElement('div'); btnWrap.className='buttons';
      const vb=document.createElement('button'); vb.type='button'; vb.textContent='View'; vb.dataset.act='imgview'; vb.dataset.src=img.url||img.path; btnWrap.appendChild(vb);
      const db=document.createElement('button'); db.type='button'; db.textContent='Remove'; db.style.borderColor='#991b1b'; db.dataset.act='imgdel'; db.dataset.id=img.id; btnWrap.appendChild(db);
      meta.appendChild(btnWrap);
      t.appendChild(meta); list.appendChild(t);
    });
    block.style.display='block';
  }else{
    block.style.display='none';
  }
  document.getElementById('recordModal').style.display='flex';
}

function closeRecordModal(){ document.getElementById('recordModal').style.display='none'; }

function openImageViewer(arr,start){
  const wrap=document.getElementById('imgViewer'); const img=document.getElementById('imgViewImg');
  try{ window.IMG_VIEW={arr:arr||[], idx:Math.max(0,Math.min(start||0,(arr||[]).length-1))}; }catch{ window.IMG_VIEW={arr:[],idx:0}; }
  const render=()=>{ img.src=window.IMG_VIEW.arr[window.IMG_VIEW.idx]||''; };
  render();
  wrap.style.display='flex';
  const prev=document.getElementById('imgViewPrev'); const next=document.getElementById('imgViewNext'); const close=document.getElementById('imgViewClose');
  if(prev) prev.onclick=(e)=>{ e.stopPropagation(); if(window.IMG_VIEW.idx>0){ window.IMG_VIEW.idx--; render(); } };
  if(next) next.onclick=(e)=>{ e.stopPropagation(); if(window.IMG_VIEW.idx<window.IMG_VIEW.arr.length-1){ window.IMG_VIEW.idx++; render(); } };
  if(close) close.onclick=()=>{ wrap.style.display='none'; };
  wrap.onclick=()=>{ wrap.style.display='none'; };
  function esc(e){ if(e.key==='Escape'){ wrap.style.display='none'; document.removeEventListener('keydown', esc);} if(e.key==='ArrowLeft'){ if(window.IMG_VIEW.idx>0){ window.IMG_VIEW.idx--; render(); } } if(e.key==='ArrowRight'){ if(window.IMG_VIEW.idx<window.IMG_VIEW.arr.length-1){ window.IMG_VIEW.idx++; render(); } } }
  document.addEventListener('keydown', esc);
}

// Initialization
if(typeof document!=='undefined'){
  document.addEventListener('DOMContentLoaded',()=>{
    const cancel=document.getElementById('recordCancel'); if(cancel) cancel.onclick=closeRecordModal;
    const form=document.getElementById('recordForm');
    if(form){
      form.addEventListener('submit', async (e)=>{
        e.preventDefault();
        const fd=new FormData(form);
        const rid=form.elements['id'] ? String(form.elements['id'].value||'').trim() : '';
        const payload={
          profile_id:Number(fd.get('profile_id')||0),
          title:String(fd.get('title')||''),
          file_path:String(fd.get('file_path')||''),
          content:String(fd.get('content')||''),
          situation:String(fd.get('situation')||''),
          event_time:(function(){ const dt=fd.get('event_dt'); if(!dt) return null; const t=Date.parse(dt); return isNaN(t)?null:Math.floor(t/1000); })(),
          description:String(fd.get('description')||'')
        };
        let url='/api/records'; let method='POST';
        if(rid){ url=`/api/records/${rid}`; method='PUT'; }
        const r=await fetch(url,{method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
        if(!r.ok){ alert('Save failed'); return; }
        const resp=await r.json().catch(()=>({}));
        const recId=rid||resp.id;
        if(!recId){ alert('Save failed'); return; }
        try{
          const imgsSel=JSON.parse(document.getElementById('selectedImagesJson').value||'[]');
          for(const rp of imgsSel){ await fetch(`/api/records/${recId}/image_remote`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({profile_id:payload.profile_id, path:rp})}); }
        }catch{}
        const files=(form.querySelector('input[name="images"]').files)||[];
        for(const f of files){ const fdf=new FormData(); fdf.append('file',f); await fetch(`/api/records/${recId}/image`,{method:'POST', body:fdf}); }
        alert('Record saved');
        closeRecordModal();
        if(window.loadRecords){ window.loadRecords(); }
      });
      const fileInput=form.querySelector('input[name="images"]');
      if(fileInput){ fileInput.addEventListener('change',()=>{
        const list=document.getElementById('selectedImagesList'); const block=document.getElementById('selectedImagesBlock');
        block.style.display='block';
        for(const f of (fileInput.files||[])){
          try{
            const url=URL.createObjectURL(f);
            const t=document.createElement('div'); t.className='thumb';
            const im=document.createElement('img'); im.src=url; t.appendChild(im);
            const m=document.createElement('div'); m.className='meta';
            const n=document.createElement('div'); n.className='name'; n.textContent=f.name; m.appendChild(n);
            const btns=document.createElement('div'); btns.className='buttons';
            const b=document.createElement('button'); b.type='button'; b.textContent='View'; b.dataset.act='imgview'; b.dataset.src=url; btns.appendChild(b);
            m.appendChild(btns);
            t.appendChild(m);
            list.appendChild(t);
          }catch{}
        }
      }); }
      const list=document.getElementById('selectedImagesList');
      if(list){ list.addEventListener('click', async (e)=>{
        const btn=e.target.closest('button'); if(!btn) return;
        if(btn.dataset.act==='imgview'){
          const imgs=[...list.querySelectorAll('img')].map(im=>im.src); const idx=imgs.indexOf(btn.dataset.src); openImageViewer(imgs, idx>=0?idx:0); return;
        }
        if(btn.dataset.act==='imgdel'){
          const iid=btn.dataset.id; if(iid){ await fetch(`/api/record_images/${iid}`,{method:'DELETE'}); if(btn.closest('.thumb')) btn.closest('.thumb').remove(); if(window.loadRecords){ window.loadRecords(); } }
        }
      }); }
    }
    const imgWrap=document.getElementById('imgViewer'); if(imgWrap){ imgWrap.style.display='none'; }
  });
}
