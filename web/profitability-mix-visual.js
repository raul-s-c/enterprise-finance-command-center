/* Published family and quality-tier economics: two reconciled views of one mix. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const value=row=>Number(row?.[metric])||0;
  const money=amount=>`${amount<0?'-':''}€${(Math.abs(amount)/1e6).toFixed(1)}m`;
  let metric='revenue';
  function controls(){
    return `<div class="pm-switch" role="group" aria-label="Compare profitability measure"><button type="button" data-pm-metric="revenue" aria-pressed="${metric==='revenue'}">Revenue</button><button type="button" data-pm-metric="operating_contribution" aria-pressed="${metric==='operating_contribution'}">Operating contribution</button></div>`;
  }
  function selected(rows,division){
    return (rows||[]).filter(row=>division==='all'||row.division===division);
  }
  function family(rows){
    if(!rows.length)return '<p class="pm-empty">No published family economics for this scope.</p>';
    const ranked=[...rows].sort((a,b)=>value(b)-value(a));
    const total=ranked.reduce((sum,row)=>sum+value(row),0);
    const top=ranked.slice(0,6).map(row=>({name:`${row.division} · ${row.product_family}`,amount:value(row),margin:Number(row.gross_margin_pct)||0}));
    if(ranked.length>6)top.push({name:`Other ${ranked.length-6} families`,amount:ranked.slice(6).reduce((sum,row)=>sum+value(row),0)});
    const maximum=Math.max(...top.map(row=>Math.abs(row.amount)),1);
    return `<div class="pm-visual" aria-label="Published family profitability ranking">${controls()}<div class="pm-total"><span>${metric==='revenue'?'Revenue':'Operating contribution'} · selected division</span><strong>${money(total)}</strong></div><div class="pm-list">${top.map(row=>`<div class="pm-row"><span title="${escape(row.name)}">${escape(row.name)}</span><div class="pm-track"><i style="width:${(Math.abs(row.amount)/maximum*100).toFixed(2)}%" class="${row.amount<0?'pm-negative':''}"></i></div><strong>${money(row.amount)}</strong><small>${total?`${(row.amount/total*100).toFixed(1)}% of selected`:'No share'}</small></div>`).join('')}</div><p class="pm-note">The remaining families are grouped only in this ranking; all source rows remain available below.</p></div>`;
  }
  function tiers(rows,familyRows){
    if(!rows.length)return '<p class="pm-empty">No published quality-tier economics for this scope.</p>';
    const ordered=[...rows].sort((a,b)=>a.division.localeCompare(b.division)||['Essential','Professional','Premium'].indexOf(a.quality_tier)-['Essential','Professional','Premium'].indexOf(b.quality_tier));
    const total=ordered.reduce((sum,row)=>sum+value(row),0);
    const familyTotal=familyRows.reduce((sum,row)=>sum+value(row),0);
    const maximum=Math.max(...ordered.map(row=>Math.abs(value(row))),1);
    const delta=total-familyTotal;
    return `<div class="pm-visual" aria-label="Published quality-tier economics">${controls()}<div class="pm-total"><span>${metric==='revenue'?'Revenue':'Operating contribution'} · tier cross-check</span><strong>${money(total)}</strong></div><div class="pm-tiers">${ordered.map(row=>`<div class="pm-tier"><span>${escape(row.division)}</span><strong>${escape(row.quality_tier)}</strong><div class="pm-track"><i style="width:${(Math.abs(value(row))/maximum*100).toFixed(2)}%" class="${value(row)<0?'pm-negative':''}"></i></div><b>${money(value(row))}</b></div>`).join('')}</div><p class="pm-reconcile ${Math.abs(delta)<.01?'pm-pass':'pm-fail'}">Tier total − family total: ${money(Math.abs(delta))} · ${Math.abs(delta)<.01?'reconciled':'review difference'}</p></div>`;
  }
  function decorate(html,source,division){
    if(!root.document)return html;
    const families=selected(source.product_family_profitability,division),quality=selected(source.quality_tier_profitability,division);
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();
      if(!['Family economics','Quality-tier economics'].includes(title))continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+(title==='Family economics'?family(families):tiers(quality,families))+`<details class="pm-source"><summary>View published source table</summary>${original}</details>`;
      panel.classList.add('pm-panel');
    }
    return host.innerHTML;
  }
  root.FinanceProfitabilityMix={selected,family,tiers,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers.profitability;
    renderers.profitability=function(){return decorate(before(),data,state.division);};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-pm-metric]');if(!button)return;
      metric=button.dataset.pmMetric==='operating_contribution'?'operating_contribution':'revenue';render();
    });
  }
})(globalThis);
