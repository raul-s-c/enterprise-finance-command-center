/* Group OPEX mix and trend from published Actual, workforce and divisional rows. */
(function(root){
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const money=value=>finite(value)?`${value<0?'−':''}€${(Math.abs(value)/1e6).toFixed(1)}m`:'—';
  const exact=value=>finite(value)?`${value<-.005?'−':''}€${(Math.abs(value)<.005?0:Math.abs(value)).toLocaleString('en-IE',{minimumFractionDigits:2,maximumFractionDigits:2})}`:'—';
  const prior=month=>`${Number(month.slice(0,4))-1}${month.slice(4)}`;
  let selectedMonth=null;

  function model(source){
    const workforce=new Map();
    for(const row of source.workforce_summary||[]){
      const entry=workforce.get(row.month)||{count:0,personnel:0};
      entry.count++;
      if(finite(row.personnel_cost))entry.personnel+=row.personnel_cost;
      workforce.set(row.month,entry);
    }
    const divisions=new Map();
    for(const row of source.management_detail||[]){
      const month=divisions.get(row.month)||new Map();
      month.set(row.division,(month.get(row.division)||0)+(finite(row.opex)?row.opex:0));
      divisions.set(row.month,month);
    }
    return (source.actual||[]).filter(row=>row.month<=source.meta.end_month).map(row=>{
      const workforceRow=workforce.get(row.month);
      const personnel=workforceRow?.count===1?workforceRow.personnel:null;
      const opex=finite(row.opex)?row.opex:null;
      const nonPeople=finite(opex)&&finite(personnel)?opex-personnel:null;
      const byDivision=[...(divisions.get(row.month)||new Map())].map(([division,value])=>({division,value})).sort((a,b)=>b.value-a.value);
      const divisionTotal=byDivision.reduce((sum,item)=>sum+item.value,0);
      return {month:row.month,opex,personnel,nonPeople,byDivision,divisionTotal,
        divisionGap:finite(opex)?divisionTotal-opex:null,
        workforceCount:workforceRow?.count||0};
    }).sort((a,b)=>a.month.localeCompare(b.month));
  }

  function visual(source,month=selectedMonth){
    const history=model(source),windowRows=history.slice(-12);
    if(!windowRows.length)return '<p class="ox-empty">No published OPEX history is available.</p>';
    const current=windowRows.find(row=>row.month===month)||windowRows.at(-1);
    const py=history.find(row=>row.month===prior(current.month));
    const delta=finite(py?.opex)&&finite(current.opex)?current.opex-py.opex:null;
    const mixValid=finite(current.personnel)&&finite(current.nonPeople)&&current.opex>0&&current.personnel>=0&&current.nonPeople>=0;
    const personnelShare=mixValid?current.personnel/current.opex*100:null;
    const max=Math.max(...windowRows.map(row=>Math.max(row.opex||0,0)),1);
    const divisionMax=Math.max(...current.byDivision.map(row=>Math.max(row.value,0)),1);
    const gap=current.divisionGap,divisionPass=finite(gap)&&Math.abs(gap)<=.05;
    return `<section class="ox-visual" aria-label="Group OPEX composition and twelve-month trend">
      <div class="ox-headline"><div><small>Selected close · ${esc(current.month)}</small><strong>${money(current.opex)}</strong><span>Total group OPEX · actual</span></div><div><small>Δ vs prior year</small><strong class="${delta===null?'':delta>0?'ox-adverse':'ox-favorable'}">${delta===null?'—':`${delta>0?'+':delta<0?'−':''}${money(Math.abs(delta))}`}</strong><span>Cost increase is adverse</span></div><div><small>Personnel share</small><strong>${personnelShare===null?'—':`${personnelShare.toFixed(1)}%`}</strong><span>of published group OPEX</span></div></div>
      <div class="ox-layout"><div class="ox-mix"><h3>What makes up OPEX</h3><p>Personnel is published by workforce; the remainder is a disclosed difference.</p>
        ${mixValid?`<div class="ox-mix-bar" role="img" aria-label="Personnel ${money(current.personnel)}, non-people ${money(current.nonPeople)}"><i style="width:${personnelShare.toFixed(2)}%"></i><i style="width:${(100-personnelShare).toFixed(2)}%"></i></div>`:'<p class="ox-warning">A valid personnel/non-people split is unavailable; no balancing allocation is shown.</p>'}
        <div class="ox-mix-values"><span><i></i>Personnel <b>${money(current.personnel)}</b></span><span><i></i>Non-people <b>${money(current.nonPeople)}</b></span></div>
        <h3>OPEX by division</h3><div class="ox-divisions">${current.byDivision.map(row=>`<div class="ox-division"><span>${esc(row.division)}</span><div class="ox-track"><i style="width:${(Math.max(row.value,0)/divisionMax*100).toFixed(2)}%"></i></div><b>${money(row.value)}</b></div>`).join('')||'<p>No divisional source rows.</p>'}</div>
        <p class="ox-check ${divisionPass?'ox-pass':'ox-fail'}">Division source total − group OPEX: ${exact(gap)} · ${divisionPass?'reconciled':'review difference'}</p>
      </div><div class="ox-history"><h3>Twelve published closes</h3><p>Personnel and residual non-people OPEX · select a month</p>
        <div class="ox-trend" role="group" aria-label="Select OPEX close month">${windowRows.map(row=>{
          const split=finite(row.personnel)&&finite(row.nonPeople)&&row.personnel>=0&&row.nonPeople>=0;
          return `<button type="button" data-ox-month="${esc(row.month)}" aria-pressed="${row.month===current.month}" aria-label="${esc(row.month)}: total OPEX ${money(row.opex)}, personnel ${money(row.personnel)}, non-people ${money(row.nonPeople)}"><span class="ox-stack">${split?`<i class="ox-people" style="height:${(row.personnel/max*100).toFixed(2)}%"></i><i class="ox-other" style="height:${(row.nonPeople/max*100).toFixed(2)}%"></i>`:`<i class="ox-unknown" style="height:${(Math.max(row.opex||0,0)/max*100).toFixed(2)}%"></i>`}</span><span>${esc(row.month.slice(5))}</span></button>`;
        }).join('')}</div><div class="ox-selected"><span>${esc(current.month)} group OPEX</span><strong>${money(current.opex)}</strong><span>Personnel</span><b>${money(current.personnel)}</b><span>Non-people difference</span><b>${money(current.nonPeople)}</b></div>
        <p class="ox-note">Division bars are posted OPEX by division. The group personnel split is not allocated to divisions.</p>
      </div></div>
      <details class="ox-source"><summary>View published source values</summary><p>Sources: <code>actual.opex</code>, <code>workforce_summary.personnel_cost</code>, <code>management_detail.opex</code>. Non-people = Actual OPEX − personnel; it is not an invoice allocation.</p><div class="ox-source-scroll"><table><thead><tr><th>Month</th><th>Actual OPEX</th><th>Personnel</th><th>Non-people difference</th><th>Division total</th><th>Gap</th></tr></thead><tbody>${windowRows.map(row=>`<tr><th>${esc(row.month)}</th><td>${exact(row.opex)}</td><td>${exact(row.personnel)}</td><td>${exact(row.nonPeople)}</td><td>${exact(row.divisionTotal)}</td><td>${exact(row.divisionGap)}</td></tr>`).join('')}</tbody></table></div></details>
    </section>`;
  }

  function decorate(html,source){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      if(panel.querySelector('.panel-title')?.textContent.trim()!=='OPEX composition')continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const subtitle=head.querySelector('.panel-sub');if(subtitle)subtitle.textContent='Source-tied mix, divisional contribution and twelve-month trend';
      panel.innerHTML=head.outerHTML+`<div class="ox-body">${visual(source)}</div>`;
      panel.classList.add('ox-panel');
    }
    return host.innerHTML;
  }

  const api={model,visual,decorate};
  root.FinanceOpexComposition=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root.document&&typeof renderers!=='undefined'){
    const previous=renderers.pnl;
    renderers.pnl=function(){return decorate(previous(),data);};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-ox-month]');if(!button)return;
      const body=button.closest('.ox-body');if(!body)return;
      selectedMonth=button.dataset.oxMonth;
      body.innerHTML=visual(data,selectedMonth);
      [...body.querySelectorAll('[data-ox-month]')].find(item=>item.dataset.oxMonth===selectedMonth)?.focus();
    });
  }
})(globalThis);
