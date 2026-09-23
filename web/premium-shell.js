/* Premium finance application shell: useful global commands, never fake chrome. */
(function(root){
  const escapeCsv=value=>`"${String(value??'').replaceAll('"','""')}"`;
  function exportView(){
    const rows=[...document.querySelectorAll('#content table tr')].map(row=>[...row.children].map(cell=>cell.textContent.trim()));
    if(!rows.length){root.print();return;}
    const csv=rows.map(row=>row.map(escapeCsv).join(',')).join('\r\n');
    const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),link=document.createElement('a');
    link.href=URL.createObjectURL(blob);link.download=`aureon-${state.view}-${data?.meta?.end_month||'report'}.csv`;link.click();URL.revokeObjectURL(link.href);
  }
  function openHelp(){const button=document.getElementById('reportHelp');if(button&&!button.hidden){button.click();return;}reportDialog('Aureon Finance help','<div class="help-pages"><p>Use the left navigation to change the reporting domain. Every financial view preserves the published close, shows only supported scope controls and provides source evidence where available.</p><p>Use contribution analysis to move from a consolidated total to entity, division, component and underlying records without allocating missing dimensions.</p></div>');}
  function searchIndex(){
    const unique=values=>[...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    return [
      ...views.map(([id,label,description])=>({type:'Report',label,detail:description,value:id})),
      ...unique((data?.management_detail||[]).map(row=>row.entity)).map(value=>({type:'Entity',label:value,detail:'Open the P&L filtered to this entity',value})),
      ...unique((data?.management_detail||[]).map(row=>row.division)).map(value=>({type:'Division',label:value,detail:'Open the P&L filtered to this division',value}))
    ];
  }
  function setupSearch(){
    const input=document.getElementById('globalSearch'),results=document.getElementById('globalSearchResults');
    if(!input||!results||input.dataset.bound)return;
    input.dataset.bound='1';
    const entries=searchIndex();let matches=[],active=-1;
    const close=()=>{results.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;};
    const choose=item=>{
      if(!item)return;
      close();input.value='';
      if(item.type==='Report')state.view=item.value;
      else if(item.type==='Entity'){state.view='pnl';state.entity=item.value;state.division='all';}
      else{state.view='pnl';state.entity='all';state.division=item.value;}
      reportState.page=0;reportState.section=null;render();
      const heading=document.getElementById('viewTitle');
      heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});
    };
    const paint=()=>{
      const query=input.value.trim().toLocaleLowerCase();
      results.replaceChildren();active=-1;input.removeAttribute('aria-activedescendant');
      if(!query){close();return;}
      const rank=item=>{
        const label=item.label.toLocaleLowerCase(),detail=item.detail.toLocaleLowerCase();
        return label===query?0:label.startsWith(query)?1:label.includes(query)?2:detail.includes(query)?3:99;
      };
      matches=entries.map(item=>({item,rank:rank(item)})).filter(row=>row.rank<99)
        .sort((a,b)=>a.rank-b.rank||a.item.label.localeCompare(b.item.label)).slice(0,8).map(row=>row.item);
      if(!matches.length){
        const empty=document.createElement('div');empty.className='global-search-empty';empty.setAttribute('role','status');empty.textContent='No reports, entities or divisions match this search.';
        results.append(empty);
      }else matches.forEach((item,index)=>{
        const option=document.createElement('div');option.id=`global-search-option-${index}`;option.tabIndex=-1;
        option.className='global-search-option';option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.dataset.searchIndex=String(index);
        const title=document.createElement('span');title.className='global-search-option-title';title.textContent=item.label;
        const kind=document.createElement('span');kind.className='global-search-option-kind';kind.textContent=item.type;
        const detail=document.createElement('small');detail.textContent=item.detail;
        option.append(title,kind,detail);results.append(option);
      });
      results.hidden=false;input.setAttribute('aria-expanded','true');
    };
    const activate=index=>{
      if(!matches.length)return;
      active=(index+matches.length)%matches.length;
      results.querySelectorAll('[role=option]').forEach((option,i)=>option.setAttribute('aria-selected',String(i===active)));
      input.setAttribute('aria-activedescendant',`global-search-option-${active}`);
    };
    input.addEventListener('input',paint);
    input.addEventListener('keydown',event=>{
      if(event.key==='ArrowDown'){event.preventDefault();if(results.hidden)paint();activate(active+1);}
      else if(event.key==='ArrowUp'){event.preventDefault();if(results.hidden)paint();activate(active<0?matches.length-1:active-1);}
      else if(event.key==='Enter'&&!results.hidden){event.preventDefault();choose(matches[active<0?0:active]);}
      else if(event.key==='Escape'&&!results.hidden){event.preventDefault();close();}
    });
    results.addEventListener('click',event=>{const option=event.target.closest('[data-search-index]');if(option)choose(matches[Number(option.dataset.searchIndex)]);});
    document.addEventListener('click',event=>{if(!results.contains(event.target)&&!input.closest('.global-search').contains(event.target))close();});
    if(input.value.trim())paint();
  }
  root.mountPremiumShell=function(){
    const period=document.getElementById('globalPeriod'),control=document.getElementById('globalControl');
    if(data?.meta?.end_month)period.textContent=data.meta.end_month;
    if(data?.validation){control.innerHTML=`<i></i> Controls ${data.validation.passed?'passed':'failed'}`;control.classList.toggle('failed',!data.validation.passed);}
    setupSearch();
    document.getElementById('globalExport').onclick=exportView;document.getElementById('globalHelp').onclick=openHelp;
  };
})(globalThis);
