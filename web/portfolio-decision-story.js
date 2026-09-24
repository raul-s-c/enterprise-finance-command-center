/* Published product lifecycle decisions, shown as a dated company narrative. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const labels={PHASE_OUT_APPROVED:'Phase-out approved',PHASE_OUT_EFFECTIVE:'Phase-out effective',REPLACEMENT_APPROVED:'Replacement approved',PRODUCT_LAUNCH:'Product launched'};
  let selectedMonth='';
  function months(endMonth,count=12){
    const [year,month]=endMonth.split('-').map(Number);
    return Array.from({length:count},(_,index)=>new Date(Date.UTC(year,month-count+index,1)).toISOString().slice(0,7));
  }
  function story(rows,endMonth,focus=selectedMonth){
    const window=months(endMonth),counts=new Map(window.map(month=>[month,0]));
    for(const row of rows||[])if(counts.has(row.month))counts.set(row.month,counts.get(row.month)+1);
    const active=counts.get(focus)?focus:[...window].reverse().find(month=>counts.get(month))||endMonth;
    const chosen=(rows||[]).filter(row=>row.month===active);
    const total=[...counts.values()].reduce((sum,count)=>sum+count,0);
    const maximum=Math.max(...counts.values(),1);
    return `<div class="pd-visual" aria-label="Published portfolio decision timeline">
      <div class="pd-summary"><div><span>12-month decisions</span><strong>${total}</strong></div><div><span>${escape(active)} decisions</span><strong>${chosen.length}</strong></div><p>Rule-based decisions, not assigned financial benefits.</p></div>
      <div class="pd-timeline" role="group" aria-label="Select a month with portfolio events">${window.map(month=>{
        const count=counts.get(month),bar=`<i style="height:${(count/maximum*100).toFixed(2)}%"></i>`;
        return count?`<button type="button" data-pd-month="${month}" aria-pressed="${month===active}" aria-label="${month}: ${count} portfolio decisions"><span>${count}</span><div>${bar}</div><small>${escape(month.slice(2))}</small></button>`:`<div class="pd-inactive" aria-label="${month}: no decisions"><span>0</span><div></div><small>${escape(month.slice(2))}</small></div>`;
      }).join('')}</div>
      <div class="pd-events"><h4>Decisions in ${escape(active)}</h4><div class="pd-cards">${chosen.map(row=>{
        const tone=row.event==='PHASE_OUT_APPROVED'?'warn':row.event==='PRODUCT_LAUNCH'?'success':'neutral';
        return `<article class="pd-card ${tone}"><div><span>${escape(row.division)} · ${escape(row.product_family)}</span><strong>${escape(row.product)}</strong></div><b>${escape(labels[row.event]||row.event)}</b><small>Effective ${escape(row.effective_month||row.month)}${row.successor?` · successor ${escape(row.successor)}`:''}</small><p>${escape(row.reason)}</p></article>`;
      }).join('')||'<p class="pd-empty">No decision in this month.</p>'}</div></div>
      <p class="pd-note">Click a month with decisions; original lifecycle events remain available below.</p>
    </div>`;
  }
  function decorate(html,source){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      if(panel.querySelector('.panel-title')?.textContent.trim()!=='Portfolio decisions')continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+story(source.portfolio_events,source.meta.end_month)+`<details class="pd-source"><summary>View published decision register</summary>${original}</details>`;
      panel.classList.add('pd-panel');
    }
    return host.innerHTML;
  }
  root.FinancePortfolioStory={months,story,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers['operations-capex'];
    renderers['operations-capex']=function(){return decorate(before(),data);};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-pd-month]');if(!button)return;
      selectedMonth=button.dataset.pdMonth;render();
    });
  }
})(globalThis);
