/* Frozen budget and published forecast vintages; visual only, no new planning model. */
(function(root){
  const sum=(rows,key)=>(rows||[]).reduce((total,row)=>total+(Number(row[key])||0),0);
  const money=value=>`${value<0?'−':''}€${(Math.abs(value)/1e6).toFixed(1)}m`;
  let selected='revenue';
  let selectedYtd='revenue';
  let selectedYtdMonth=null;
  function months(rows){
    const byMonth=new Map();
    for(const row of rows||[]){
      const current=byMonth.get(row.month)||{month:row.month,revenue:0,revenue_budget:0,ebit:0,ebit_budget:0};
      for(const key of ['revenue','revenue_budget','ebit','ebit_budget'])current[key]+=Number(row[key])||0;
      byMonth.set(row.month,current);
    }
    return [...byMonth.values()].sort((a,b)=>a.month.localeCompare(b.month));
  }
  function performance(source,metric=selectedYtd,month=selectedYtdMonth){
    const key=metric==='ebit'?'ebit':'revenue',rows=months(source),budgetKey=`${key}_budget`;
    if(!rows.length)return '<p class="po-empty">No published YTD budget comparison for this scope.</p>';
    const actual=sum(rows,key),budget=sum(rows,budgetKey),delta=actual-budget;
    const selectedRow=rows.find(row=>row.month===month)||rows.at(-1);
    const values=rows.flatMap(row=>[row[key],row[budgetKey]]),minimum=Math.min(...values,0),maximum=Math.max(...values,0),range=maximum-minimum||1;
    const x=index=>20+index*400/Math.max(rows.length-1,1),y=value=>89-(value-minimum)/range*72;
    const line=field=>rows.map((row,index)=>`${index?'L':'M'}${x(index).toFixed(2)},${y(row[field]).toFixed(2)}`).join(' ');
    return `<div class="po-ytd" aria-label="Monthly actual versus frozen Budget ${key} for the selected scope">
      <div class="po-head"><div><span>YTD ${key} · AC vs Budget</span><strong class="${delta<0?'po-adverse':'po-favorable'}">${delta<0?'−':'+'}${money(Math.abs(delta))}</strong><small>AC ${money(actual)} · Budget ${money(budget)}</small></div><div class="po-switch" role="group" aria-label="YTD measure"><button type="button" data-po-ytd-metric="revenue" aria-pressed="${key==='revenue'}">Revenue</button><button type="button" data-po-ytd-metric="ebit" aria-pressed="${key==='ebit'}">EBIT</button></div></div>
      <div class="po-ytd-legend"><span><i class="po-ac-key"></i>AC · Actual</span><span><i class="po-b-key"></i>B · frozen Budget</span><span>EUR million</span></div>
      <svg class="po-ytd-chart" viewBox="0 0 440 104" preserveAspectRatio="none" role="img" aria-label="${rows.map(row=>`${row.month}: Actual ${money(row[key])}, Budget ${money(row[budgetKey])}`).join('; ')}"><line class="po-ytd-zero" x1="20" x2="420" y1="${y(0).toFixed(2)}" y2="${y(0).toFixed(2)}"/><path class="po-ytd-budget" d="${line(budgetKey)}"/><path class="po-ytd-actual" d="${line(key)}"/>${rows.map((row,index)=>`<circle class="po-ytd-point ${row.month===selectedRow.month?'is-selected':''}" cx="${x(index).toFixed(2)}" cy="${y(row[key]).toFixed(2)}" r="${row.month===selectedRow.month?4:2.4}"/>`).join('')}</svg>
      <div class="po-ytd-months" role="group" aria-label="Select YTD month" style="grid-template-columns:repeat(${rows.length},minmax(0,1fr))">${rows.map(row=>`<button type="button" data-po-ytd-month="${row.month}" aria-pressed="${row.month===selectedRow.month}">${row.month.slice(5)}</button>`).join('')}</div>
      <div class="po-ytd-selected"><strong>${selectedRow.month}</strong><span>AC ${money(selectedRow[key])}</span><span>Budget ${money(selectedRow[budgetKey])}</span><b class="${selectedRow[key]-selectedRow[budgetKey]<0?'po-adverse':'po-favorable'}">Δ ${selectedRow[key]-selectedRow[budgetKey]<0?'−':'+'}${money(Math.abs(selectedRow[key]-selectedRow[budgetKey]))}</b></div>
      <p class="po-note">Δ = AC − Budget · same published scope; sign is not a universal favorability marker.</p>
    </div>`;
  }
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
  function decorate(html,rows,ytdRows){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();
      if(!['FY outlook evolution','YTD performance'].includes(title))continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+(title==='FY outlook evolution'?outlook(rows):performance(ytdRows))+`<details class="po-source"><summary>View published source table</summary>${original}</details>`;
      panel.classList.add('po-panel');
    }
    return host.innerHTML;
  }
  root.FinancePlanOutlook={months,performance,outlook,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const previous=renderers.forecast;
    renderers.forecast=function(){return decorate(previous(),scopedPlan(data.fy_plan_bridge||[]),scopedPlan(data.budget_performance||[]));};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-po-metric]');if(!button)return;
      selected=button.dataset.poMetric==='ebit'?'ebit':'revenue';
      const visual=button.closest('.po-visual');if(visual)visual.outerHTML=outlook(scopedPlan(data.fy_plan_bridge||[]),selected);
    });
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-po-ytd-metric]');if(!button)return;
      selectedYtd=button.dataset.poYtdMetric==='ebit'?'ebit':'revenue';
      const visual=button.closest('.po-ytd');if(visual)visual.outerHTML=performance(scopedPlan(data.budget_performance||[]),selectedYtd);
    });
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-po-ytd-month]');if(!button)return;
      selectedYtdMonth=button.dataset.poYtdMonth;
      const visual=button.closest('.po-ytd');if(visual)visual.outerHTML=performance(scopedPlan(data.budget_performance||[]),selectedYtd,selectedYtdMonth);
    });
  }
})(globalThis);
