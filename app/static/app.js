let state = {
  profiles: [],
  selected: new Set(),
};

function cssEscape(s){
  try{ return (window.CSS && CSS.escape)? CSS.escape(String(s)) : String(s).replace(/[^a-zA-Z0-9_-]/g, '_'); }
  catch{ return String(s).replace(/[^a-zA-Z0-9_-]/g, '_'); }
}

// Simple inline folder SVG used in directory-style headers
const SVG_FOLDER = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 6a2 2 0 012-2h5l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V6z"/></svg>';

// Debug + simple prefs helpers
function dbg(){ try{ if((window.APP_CFG && window.APP_CFG.debug) || window.DEBUG_UI){ console.log('[UI]', ...arguments); } }catch{} }
const PREF_NS = 'sshlt_';
function setPref(key, val){ const k=PREF_NS+key; try{ localStorage.setItem(k, JSON.stringify(val)); }catch{} try{ document.cookie = `${k}=${encodeURIComponent(JSON.stringify(val))}; path=/; max-age=31536000`; }catch{} }
function getPref(key, def){ const k=PREF_NS+key; try{ const v=localStorage.getItem(k); if(v!=null) return JSON.parse(v); }catch{} try{ const m=document.cookie.match(new RegExp('(?:^|; )'+k+'=([^;]*)')); if(m) return JSON.parse(decodeURIComponent(m[1])); }catch{} return def; }
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
function escapeHtml(s){ return String(s||'').replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function setRunMessage(text, cls){ const el=document.getElementById('runMsg'); if(!text){ el.style.display='none'; return; } el.className = 'alert ' + (cls||'info'); el.textContent=text; el.style.display='block'; }

async function loadProfiles(){
  const {ok, data} = await fetchJSON('/api/profiles');
  const list = (ok && data.profiles) || [];
  state.profiles = list;
  const tbody = document.querySelector('#profilesTable tbody'); tbody.innerHTML='';
  // restore selection
  try{ state.selected = new Set(getPref('logs.selectedProfiles', [])); }catch{}
  list.forEach(p=>{
    const tr = document.createElement('tr');
    const checked = state.selected.has(p.id);
    tr.innerHTML = `<td><input type="checkbox" ${checked?'checked':''} data-id="${p.id}"></td><td>${escapeHtml(p.name)}</td><td class="muted">${escapeHtml(p.protocol)}</td>`;
    tbody.appendChild(tr);
  });
  dbg('loadProfiles: restored selected', Array.from(state.selected));
}

function collectSelected(){
  state.selected.clear();
  document.querySelectorAll('#profilesTable input[type="checkbox"]').forEach(cb=>{ if(cb.checked) state.selected.add(Number(cb.dataset.id)); });
}

function ensureProfileFolder(tbody, profileId, profileName){
  let folder = tbody.querySelector(`tr.folder-row[data-pid="${profileId}"]`);
  if(folder) return folder;
  folder = document.createElement('tr');
  folder.className = 'folder-row result-row expanded';
  folder.dataset.pid = String(profileId);
  folder.innerHTML = `<td colspan="3"><span class="caret"></span>${SVG_FOLDER}<strong style="margin-left:6px;">${escapeHtml(profileName)}</strong></td>`;
  const container = document.createElement('tr');
  container.className = 'folder-container';
  const td = document.createElement('td'); td.colSpan = 3; container.appendChild(td);
  tbody.appendChild(folder); tbody.appendChild(container);
  folder.addEventListener('click', ()=>{
    folder.classList.toggle('expanded');
    td.style.display = (td.style.display==='none')? '' : 'none';
  });
  return folder;
}

function addPathResultsUnder(tbody, profileId, profileName, path, lines, maxLines){
  ensureProfileFolder(tbody, profileId, profileName);
  const containerTd = tbody.querySelector(`tr.folder-row[data-pid="${profileId}"] + tr.folder-container td`);
  const block = document.createElement('div'); block.className='path-block';
  const title = document.createElement('div'); title.className='path-title'; title.innerHTML = `<span class="caret"></span>${SVG_FOLDER}<span>${escapeHtml(path)}</span><span class="badge">text</span>`;
  const tbl = document.createElement('table'); tbl.className='lines-table';
  const tb = document.createElement('tbody');
  const maxN = Math.max(1, parseInt(maxLines||200,10));
  const arr = (lines||[]).slice(-maxN);
  arr.forEach((ln, idx)=>{
    const r = document.createElement('tr'); r.style.cursor='pointer';
    r.innerHTML = `<td style="width:56px" class="muted">${idx+1}</td><td>${escapeHtml(ln)}</td>`;
    r.onclick = ()=> openRecordModal(profileId, path, ln);
    tb.appendChild(r);
  });
  tbl.appendChild(tb);
  block.appendChild(title); block.appendChild(tbl);
  // collapse/expand per path
  block.classList.add('expanded');
  title.style.cursor = 'pointer';
  title.addEventListener('click', ()=>{
    block.classList.toggle('expanded');
    tbl.style.display = (tbl.style.display==='none')? '' : 'none';
  });
  containerTd.appendChild(block);
}

function addTextFileResultsUnder(tbody, profileId, profileName, basePath, filePath, lines, maxLines){
  ensureProfileFolder(tbody, profileId, profileName);
  const containerTd = tbody.querySelector(`tr.folder-row[data-pid="${profileId}"] + tr.folder-container td`);
  // Group per base path: find or create a wrapper block
  let wrapper = containerTd.querySelector(`div.path-block[data-base="${cssEscape(basePath)}"]`);
  if(!wrapper){
    wrapper = document.createElement('div'); wrapper.className='path-block'; wrapper.dataset.base = basePath;
  const title = document.createElement('div'); title.className='path-title'; title.innerHTML = `<span class="caret"></span>${SVG_FOLDER}<span>${escapeHtml(basePath)}</span><span class="badge">text</span>`;
    const container = document.createElement('div'); container.className='files-container';
    wrapper.appendChild(title); wrapper.appendChild(container);
    title.style.cursor='pointer';
    title.addEventListener('click', ()=>{ container.style.display = (container.style.display==='none')? '' : 'none'; });
    containerTd.appendChild(wrapper);
  }
  const filesContainer = wrapper.querySelector('.files-container');
  // Each file gets its own small table
  const block = document.createElement('div'); block.className='path-block';
  const title = document.createElement('div'); title.className='path-title'; title.innerHTML = `<span class="caret"></span>${SVG_FOLDER}<span>${escapeHtml(filePath)}</span>`;
  const tbl = document.createElement('table'); tbl.className='lines-table';
  const tb = document.createElement('tbody');
  const maxN = Math.max(1, parseInt(maxLines||200,10));
  const arr = (lines||[]).slice(-maxN);
  arr.forEach((ln, idx)=>{
    const r = document.createElement('tr'); r.style.cursor='pointer';
    r.innerHTML = `<td style=\"width:56px\" class=\"muted\">${idx+1}</td><td>${escapeHtml(ln)}</td>`;
    r.onclick = ()=> openRecordModal(profileId, filePath, ln);
    tb.appendChild(r);
  });
  tbl.appendChild(tb);
  block.appendChild(title); block.appendChild(tbl);
  title.style.cursor='pointer';
  title.addEventListener('click', ()=>{ tbl.style.display = (tbl.style.display==='none')? '' : 'none'; });
  filesContainer.appendChild(block);
}

function addImageResultsUnder(tbody, profileId, profileName, path, files){
  ensureProfileFolder(tbody, profileId, profileName);
  const containerTd = tbody.querySelector(`tr.folder-row[data-pid="${profileId}"] + tr.folder-container td`);
  const block = document.createElement('div'); block.className='path-block';
  const title = document.createElement('div'); title.className='path-title'; title.innerHTML = `<span class="caret"></span>${SVG_FOLDER}<span>${escapeHtml(path)}</span><span class="badge">images</span>`;
  const tbl = document.createElement('table'); tbl.className='lines-table';
  const tb = document.createElement('tbody');
  (files||[]).forEach((fp, idx)=>{
    const r = document.createElement('tr');
    r.style.cursor='pointer';
    r.classList.add('image-row');
    r.dataset.pid = String(profileId);
    r.dataset.path = fp;
    r.setAttribute('title','Click to create record from this image');
    r.innerHTML = `<td style=\"width:56px\" class=\"muted\">${idx+1}</td><td>${escapeHtml(fp)}</td>`;
    tb.appendChild(r);
  });
  tbl.appendChild(tb);
  block.appendChild(title); block.appendChild(tbl);
  block.classList.add('expanded');
  title.style.cursor = 'pointer';
  title.addEventListener('click', ()=>{
    block.classList.toggle('expanded');
    tbl.style.display = (tbl.style.display==='none')? '' : 'none';
  });
  containerTd.appendChild(block);
}


async function runAll(){
  const runBtn = document.getElementById('runAll');
  const oldLabel = runBtn.textContent;
  runBtn.disabled = true; runBtn.textContent = 'Running...';
  setRunMessage('Running across selected profiles...', 'info');
  try{
    collectSelected();
    try{ setPref('logs.selectedProfiles', Array.from(state.selected)); }catch{}
    const tbody = document.querySelector('#resultTable tbody'); tbody.innerHTML='';
    const maxLines = parseInt(document.getElementById('maxLines').value||getPref('logs.maxLines','200'),10);
    setPref('logs.maxLines', maxLines);
    dbg('runAll start', Array.from(state.selected), maxLines);
    for(const p of state.profiles){
      if(!state.selected.has(p.id)) continue;
      if(String(p.protocol||'').toLowerCase()!=='ssh') continue;
      // Connectivity check: skip all tasks for this profile if unreachable
      try{
        const ping = await fetchJSON(`/api/profiles/${p.id}/ping`);
        const okPing = !!(ping.ok && ping.data && ping.data.ok !== false ? ping.data.ok : false) || (ping.data && ping.data.ok === true);
        if(!okPing){
          const errMsg = (ping.data && (ping.data.error||ping.data.err)) || 'Connection failed';
          const msg = `Cannot connect to ${p.name} (${p.host||''})`;
          setRunMessage(`${msg}: ${errMsg}`, 'error');
          alert(`${msg}\n${errMsg}`);
          continue;
        }
      }catch(e){
        const msg = `Cannot connect to ${p.name}`;
        setRunMessage(msg, 'error');
        alert(msg);
        continue;
      }
      const resPaths = await fetchJSON(`/api/profiles/${p.id}/paths`);
      const paths = (resPaths.ok && resPaths.data.paths) || [];
      dbg('paths', p.name, paths);
      for(const pathObj of paths){
        const typ = String(pathObj.type||'text').toLowerCase();
        // Expand files first (auto-detect if needed)
        const qlist = new URLSearchParams();
        qlist.set('pattern', pathObj.path);
        qlist.set('type', typ==='image' ? 'image' : 'auto');
        qlist.set('limit', String(maxLines));
        const listRes = await fetchJSON(`/api/profiles/${p.id}/list?`+qlist.toString());
        if(!listRes.ok || (listRes.data && listRes.data.error)){
          const errMsg = (listRes.data && listRes.data.error) || 'List failed';
          const msg = `Stopped ${p.name}: ${errMsg}`;
          setRunMessage(msg, 'error');
          alert(msg);
          break;
        }
        const files = (listRes.data && listRes.data.files) || [];
        dbg('files', pathObj.path, files.length);
        if(typ === 'image' || (listRes.data && listRes.data.type === 'image')){
          addImageResultsUnder(tbody, p.id, p.name, pathObj.path, files);
          continue;
        }
        // Text flow: tail each file individually, honoring grep_chain
        for(const fp of files){
          const q = new URLSearchParams();
          q.set('pattern', fp);
          q.set('lines', String(maxLines));
          (pathObj.grep_chain||[]).forEach(g=> q.append('grep', g));
          const res = await fetchJSON(`/api/profiles/${p.id}/cat?`+q.toString());
          if(!res.ok || (res.data && res.data.error)){
            const errMsg = (res.data && res.data.error) || 'Connection or command failed';
            const msg = `Stopped ${p.name}: ${errMsg}`;
            setRunMessage(msg, 'error');
            alert(msg);
            break; // cancel remaining files for this path/profile
          }
          addTextFileResultsUnder(tbody, p.id, p.name, pathObj.path, fp, (res.ok && res.data.lines)||[], maxLines);
        }
      }
    }
    setRunMessage('Done', 'info');
  } catch (err){
    setRunMessage('Run failed: '+ String(err), 'error');
  } finally {
    runBtn.disabled = false; runBtn.textContent = oldLabel;
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadProfiles();
  // restore maxLines
  try{ const ml = getPref('logs.maxLines'); if(ml){ document.getElementById('maxLines').value = ml; } }catch{}
  document.getElementById('profilesTable').addEventListener('change', (e)=>{ const cb = e.target.closest('input[type="checkbox"]'); if(!cb) return; collectSelected(); });
  document.getElementById('runAll').onclick = runAll;
  // Delegate clicks on image rows to open record modal
  const resTbl = document.getElementById('resultTable');
  if(resTbl){
    resTbl.addEventListener('click', (e)=>{
      const row = e.target.closest('tr.image-row');
      if(row){
        const pid = Number(row.dataset.pid);
        const pth = row.dataset.path;
        dbg('click image-row', {pid, pth});
        if(pth){ openImageRecordModal(pid, pth); }
      }
    });
  }
});

// Simple fullscreen image viewer
let IMG_VIEW = { arr: [], idx: 0 };
function openImageViewer(arr, start){
  try{ IMG_VIEW.arr = arr||[]; IMG_VIEW.idx = Math.max(0, Math.min(start||0, IMG_VIEW.arr.length-1)); }catch{ IMG_VIEW={arr:[], idx:0}; }
  const wrap = document.getElementById('imgViewer'); const img = document.getElementById('imgViewImg');
  if(!wrap||!img) return;
  const render = ()=>{ img.src = IMG_VIEW.arr[IMG_VIEW.idx]||''; };
  render();
  wrap.style.display='flex';
  const prev = document.getElementById('imgViewPrev'); const next = document.getElementById('imgViewNext'); const close = document.getElementById('imgViewClose');
  if(prev) prev.onclick = (e)=>{ e.stopPropagation(); if(IMG_VIEW.idx>0){ IMG_VIEW.idx--; render(); } };
  if(next) next.onclick = (e)=>{ e.stopPropagation(); if(IMG_VIEW.idx<IMG_VIEW.arr.length-1){ IMG_VIEW.idx++; render(); } };
  if(close) close.onclick = ()=>{ wrap.style.display='none'; };
  wrap.onclick = ()=>{ wrap.style.display='none'; };
  function esc(e){ if(e.key==='Escape'){ wrap.style.display='none'; document.removeEventListener('keydown', esc);} if(e.key==='ArrowLeft'){ if(IMG_VIEW.idx>0){ IMG_VIEW.idx--; render(); } } if(e.key==='ArrowRight'){ if(IMG_VIEW.idx<IMG_VIEW.arr.length-1){ IMG_VIEW.idx++; render(); } } }
  document.addEventListener('keydown', esc);
}
