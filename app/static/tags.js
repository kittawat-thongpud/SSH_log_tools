async function loadTags(){
  const r = await fetch('/api/tags');
  const data = await r.json().catch(()=>({}));
  const tb = document.querySelector('#tagsTable tbody');
  tb.innerHTML='';
  (data.tags||[]).forEach(t=>{
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${t.name}</td><td><button data-act="del" data-id="${t.id}" style="border-color:#991b1b">Delete</button></td>`;
    tb.appendChild(tr);
  });
  if(window.loadTagsCache){ window.loadTagsCache(); }
}

if(typeof document!=='undefined'){
  document.addEventListener('DOMContentLoaded',()=>{
    loadTags();
    const form=document.getElementById('tagForm');
    if(form){
      form.addEventListener('submit', async (e)=>{
        e.preventDefault();
        const name=form.name.value.trim();
        if(!name) return;
        const r=await fetch('/api/tags',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})});
        if(r.ok){ form.reset(); loadTags(); }
      });
    }
    const table=document.getElementById('tagsTable');
    table.addEventListener('click', async (e)=>{
      const btn=e.target.closest('button');
      if(!btn) return;
      if(btn.dataset.act==='del'){
        if(!confirm('Delete tag?')) return;
        const id=btn.dataset.id;
        const r=await fetch(`/api/tags/${id}`,{method:'DELETE'});
        if(r.ok){ loadTags(); }
      }
    });
  });
}
