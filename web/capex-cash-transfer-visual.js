/* CAPEX event view: SPEND uses cash; GO_LIVE transfers CIP to PPE without cash. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const money=value=>`${value<0?'-':''}€${(Math.abs(value)/1e6).toFixed(2)}m`;
  function projects(rows){
    const map=new Map();
    for(const row of rows||[]){
      const item=map.get(row.project)||{project:row.project,name:row.project_name,entity:row.entity,division:row.division,goLive:row.go_live,spend:0,transfer:0};
      if(row.event==='SPEND')item.spend+=Number(row.amount)||0;
      if(row.event==='GO_LIVE')item.transfer+=Number(row.amount)||0;
      map.set(row.project,item);
    }
    return [...map.values()].map(item=>({...item,cip:item.spend-item.transfer,status:item.transfer>0?'Live':'In progress'})).sort((a,b)=>b.spend-a.spend);
  }
  function visual(rows,balanceSheetCip){
    if(!rows.length)return '<p class="ct-empty">No published CAPEX projects.</p>';
    const spend=rows.reduce((sum,row)=>sum+row.spend,0),transfer=rows.reduce((sum,row)=>sum+row.transfer,0),cip=rows.reduce((sum,row)=>sum+row.cip,0);
    const maximum=Math.max(...rows.map(row=>row.spend),1);
    const control=Math.abs(spend-transfer-cip)<.05&&rows.every(row=>row.cip>=-.05);
    const hasBalance=balanceSheetCip!==undefined&&balanceSheetCip!==null&&Number.isFinite(Number(balanceSheetCip));
    const balanceGap=hasBalance?cip-Number(balanceSheetCip):null;
    return `<div class="ct-visual" aria-label="Published CAPEX cash and noncash project flow">
      <div class="ct-equation"><div><span>Cash SPEND → CIP</span><strong>${money(spend)}</strong></div><b>−</b><div><span>GO_LIVE → PPE</span><strong>${money(transfer)}</strong><small>Noncash transfer</small></div><b>=</b><div><span>Remaining CIP</span><strong>${money(cip)}</strong></div></div>
      <div class="ct-path"><span>SPEND: Dr 1510 CIP · Cr 1000 Cash</span><span>GO_LIVE: Dr 1500 PPE · Cr 1510 CIP</span></div>
      <div class="ct-projects">${rows.map(row=>`<div class="ct-project"><header><strong title="${escape(row.name)}">${escape(row.name)}</strong><span>${escape(row.entity)} · ${escape(row.status)}</span></header><div class="ct-bar"><i style="width:${(row.spend/maximum*100).toFixed(2)}%"></i></div><div class="ct-project-foot"><span>Cash ${money(row.spend)}</span><span>${row.transfer>0?`PPE transfer ${money(row.transfer)}`:`CIP ${money(row.cip)} · planned ${escape(row.goLive)}`}</span></div></div>`).join('')}</div>
      <p class="ct-control ${control?'ct-pass':'ct-fail'}">Project-event roll-forward: SPEND − GO_LIVE − remaining CIP = ${money(Math.abs(spend-transfer-cip))} · ${control?'reconciled':'review difference'}</p>
      <p class="ct-bs-control ${hasBalance&&Math.abs(balanceGap)<.01?'ct-pass':'ct-fail'}">Project CIP − balance-sheet CIP: ${hasBalance?`${money(Math.abs(balanceGap))} · ${Math.abs(balanceGap)<.01?'reconciled':'review difference'}`:'source unavailable'}</p>
      <p class="ct-note">GO_LIVE is noncash; GL controls run in the close.</p>
    </div>`;
  }
  function factories(rows){
    if(!rows.length)return '<p class="ct-empty">No current factory capacity schedule.</p>';
    const produced=rows.reduce((sum,row)=>sum+Number(row.produced_units||0),0);
    const capacity=rows.reduce((sum,row)=>sum+Number(row.capacity_units||0),0);
    const utilization=capacity?produced/capacity:0;
    return `<div class="ct-visual ct-factory" aria-label="Published factory utilization and capacity"><div class="ct-factory-head"><div><span>Capacity-weighted utilization</span><strong>${(utilization*100).toFixed(1)}%</strong></div><div><span>Produced units</span><strong>${Math.round(produced).toLocaleString('en-US')}</strong></div><div><span>Capacity headroom</span><strong>${Math.round(capacity-produced).toLocaleString('en-US')}</strong></div></div><div class="ct-factory-sites">${rows.map(row=>`<div class="ct-factory-site"><header><strong>${escape(row.factory_name)}</strong><span>${escape(row.factory)}</span></header><div class="ct-factory-track"><i style="width:${(Math.min(Number(row.utilization||0),1)*100).toFixed(2)}%"></i></div><div class="ct-factory-foot"><span>${(Number(row.utilization||0)*100).toFixed(1)}% utilized</span><span>${Math.round(Number(row.produced_units||0)).toLocaleString('en-US')} / ${Math.round(Number(row.capacity_units||0)).toLocaleString('en-US')} units</span></div><small>Published capacity addition: +${(Number(row.capacity_increase_pct||0)*100).toFixed(1)}%</small></div>`).join('')}</div><p class="ct-note">Group utilization = sum produced units / sum available capacity. Capacity is not a sales measure.</p></div>`;
  }
  function decorate(html,source){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();
      if(!['Factory utilization','CAPEX portfolio'].includes(title))continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      const current=(source.factory||[]).filter(row=>row.month===source.meta.end_month);
      const closeBalance=(source.balance_sheet||[]).find(row=>row.month===source.meta.end_month);
      panel.innerHTML=head.outerHTML+(title==='CAPEX portfolio'?visual(projects(source.capex),closeBalance?.cip):factories(current))+`<details class="ct-source"><summary>View published ${title==='CAPEX portfolio'?'project':'factory'} table</summary>${original}</details>`;
      panel.classList.add('ct-panel');
    }
    return host.innerHTML;
  }
  root.FinanceCapexVisual={projects,visual,factories,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers['operations-capex'];
    renderers['operations-capex']=function(){return decorate(before(),data);};
  }
})(globalThis);
