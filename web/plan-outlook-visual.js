/* Frozen budget and published forecast vintages; visual only, no new planning model. */
(function(root){
  const sum=(rows,key)=>(rows||[]).reduce((total,row)=>total+(Number(row[key])||0),0);
  const money=value=>`${value<0?'−':''}€${(Math.abs(value)/1e6).toFixed(1)}m`;
  let selected='revenue';
  function outlook(rows,metric=selected){
    const key=metric==='ebit'?'ebit':'revenue';
    const items=[['FY Budget',`fy_budget_${key}`,'Frozen plan'],['FC-6',`fc_6_fy_${key}`,'Six-month vintage'],['FC-3',`fc_3_fy_${key}`,'Three-month vintage'],['FC-1',`fc_1_fy_${key}`,'One-month vintage'],['Latest FY',`latest_fy_${key}`,'Current outlook']].map(([label,field,note])=>({label,note,value:sum(rows,field)}));
    const baseline=items[0].value,latest=items.at(-1).value,max=Math.max(...items.map(item=>Math.abs(item.value)),1);
    return `<div class="po-visual" aria-label="Full-year ${key} outlook from frozen budget through published forecast vintages">
      <div class="po-head"><div><span>Latest vs frozen Budget</span><strong class="${latest-baseline<0?'po-adverse':'po-favorable'}">${latest-baseline<0?'−':'+'}${money(Math.abs(latest-baseline))}</strong><small>FY ${key} · EUR million · selected scope</small></div><div class="po-switch" role="group" aria-label="Outlook measure"><button type="button" data-po-metric="revenue" aria-pressed="${key==='revenue'}">Revenue</button><button type="button" data-po-metric="ebit" aria-pressed="${key==='ebit'}">EBIT</button></div></div>
      <div class="po-axis"><span>Negative</span><span>0</span><span>Positive</span></div>
      <div class="po-rows">${items.map((item,index)=>`<div class="po-row ${index===0?'po-budget':index===4?'po-latest':''}" title="${item.label}: ${money(item.value)}; ${item.note}"><span class="po-name"><b>${item.label}</b><small>${item.note}</small></span><div class="po-track"><span class="po-negative">${item.value<0?`<i style="width:${(Math.abs(item.value)/max*100).toFixed(2)}%"></i>`:''}</span><span class="po-positive">${item.value>=0?`<i style="width:${(item.value/max*100).toFixed(2)}%"></i>`:''}</span></div><strong class="po-value">${money(item.value)}</strong></div>`).join('')}</div>
      <p class="po-note">FC-6, FC-3 and FC-1 are historical planning vintages; the Annual Budget stays frozen. Bars compare published full-year totals, not additive changes.</p>
    </div>`;
  }
  function decorate(html,rows){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      if(panel.querySelector('.panel-title')?.textContent.trim()!=='FY outlook evolution')continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+outlook(rows)+`<details class="po-source"><summary>View published values</summary>${original}</details>`;
      panel.classList.add('po-panel');
    }
    return host.innerHTML;
  }
  root.FinancePlanOutlook={outlook,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const previous=renderers.forecast;
    renderers.forecast=function(){return decorate(previous(),scopedPlan(data.fy_plan_bridge||[]));};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-po-metric]');if(!button)return;
      selected=button.dataset.poMetric==='ebit'?'ebit':'revenue';
      const visual=button.closest('.po-visual');if(visual)visual.outerHTML=outlook(scopedPlan(data.fy_plan_bridge||[]),selected);
    });
  }
})(globalThis);
