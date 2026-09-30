/* The review front page is assembled only from the published close and its controls. */
(function(root){
  const esc=value=>root.FinanceReport.escape(String(value??''));
  const amount=value=>{
    const number=Number(value),absolute=Math.abs(number),sign=number<0?'-':'';
    if(!Number.isFinite(number))return '—';
    if(absolute>=1e6)return `${sign}€${(absolute/1e6).toFixed(1)}m`;
    if(absolute>=1e3)return `${sign}€${(absolute/1e3).toFixed(1)}k`;
    return `${sign}€${absolute.toFixed(0)}`;
  };
  const exact=value=>Number.isFinite(Number(value))?new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(Number(value)):'—';
  const scope=(rows,selection)=>{
    if(selection.entity==='all'&&selection.division==='all')return rows.filter(row=>row.scope_level==='Group');
    if(selection.entity!=='all'&&selection.division==='all')return rows.filter(row=>row.scope_level==='Entity'&&row.entity===selection.entity);
    if(selection.entity==='all'&&selection.division!=='all')return rows.filter(row=>row.scope_level==='Division'&&row.division===selection.division);
    return rows.filter(row=>row.scope_level==='Entity Division'&&row.entity===selection.entity&&row.division===selection.division);
  };
  const active=row=>['Open','In Progress','In progress'].includes(row.status);
  function scoreCard(row,label){
    if(!row)return '';
    const actual=Number(row.actual_value),benchmark=Number(row.benchmark_value),scale=Math.max(actual,benchmark,1),bars=actual>=0&&benchmark>=0&&Number.isFinite(actual)&&Number.isFinite(benchmark);
    const pairName=row.metric==='FY EBIT outlook'?'Outlook':'Actual',benchmarkName='Budget';
    const pair=bars?`<div class="prv-pair" aria-label="${esc(benchmarkName)} ${esc(exact(benchmark))}; ${esc(pairName)} ${esc(exact(actual))}">
      <div><span>${benchmarkName}</span><i aria-hidden="true"><b class="prv-benchmark" style="width:${(benchmark/scale*100).toFixed(2)}%"></b></i><strong>${esc(amount(benchmark))}</strong></div>
      <div><span>${pairName}</span><i aria-hidden="true"><b class="prv-actual" style="width:${(actual/scale*100).toFixed(2)}%"></b></i><strong>${esc(amount(actual))}</strong></div>
    </div>`:`<div class="prv-signed-pair">${benchmarkName} ${esc(amount(benchmark))} · ${pairName} ${esc(amount(actual))}<small>Signed values; scale bars omitted</small></div>`;
    const note=row.metric==='FY EBIT outlook'?'Latest full-year outlook':`${(Number(row.materiality_pct)*100).toFixed(1)}% materiality`;
    return `<section class="kpi prv-score-card ${row.favorable?'is-favorable':'is-adverse'}"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(amount(row.variance))}</div><div class="kpi-note">${esc(note)}</div>${pair}<button class="prv-text-link" data-prv-observation="${esc(row.review_id)}">Inspect source variance <span aria-hidden="true">↗</span></button></section>`;
  }
  function statusCard(label,value,note,route){
    return `<div class="kpi prv-status"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note)}</div><button class="prv-status-route" data-prv-route="${esc(route)}" aria-label="Explore ${esc(label)}"><span aria-hidden="true">›</span></button></div>`;
  }
  function bridge(review,data,selection){
    if(selection.entity!=='all'||selection.division!=='all')return '';
    const effects=['Price effect','Volume effect','Mix effect'].map(metric=>review.find(row=>row.metric===metric));
    if(effects.some(row=>!row||row.unit!=='EUR'||!Number.isFinite(Number(row.actual_value))))return '';
    const current=data.meta.end_month,prior=`${Number(current.slice(0,4))-1}${current.slice(4)}`;
    const revenue=month=>(data.management_detail||[]).filter(row=>row.month===month).reduce((sum,row)=>sum+Number(row.revenue||0),0);
    const start=revenue(prior),end=revenue(current),deltas=effects.map(row=>Number(row.actual_value));
    if(!Number.isFinite(start)||!Number.isFinite(end)||start<=0||end<=0||Math.abs(start+deltas.reduce((sum,value)=>sum+value,0)-end)>0.01)return '';
    const points=[start];for(const delta of deltas)points.push(points.at(-1)+delta);
    const max=Math.max(start,end,...points)*1.12;
    const names=[`PY ${prior}`,'Price','Volume','Mix',`AC ${current}`];
    const values=[start,...deltas,end];
    const columns=values.map((value,index)=>{
      const total=index===0||index===4,before=points[index-1],after=points[index];
      const bottom=total?0:Math.min(before,after)/max*100,height=(total?value:Math.abs(value))/max*100;
      const signed=!total&&value>0?'+':'';
      return `<div class="prv-bridge-column" role="listitem" aria-label="${esc(names[index])} ${esc(exact(value))}"><strong class="${!total&&value<0?'is-adverse':''}">${signed}${esc(amount(value))}</strong><div class="prv-bridge-track"><i class="${total?'is-total':value<0?'is-negative':'is-positive'}" style="bottom:${bottom.toFixed(2)}%;height:${height.toFixed(2)}%"></i></div><span>${esc(names[index])}</span></div>`;
    }).join('');
    return `<div class="prv-bridge"><div class="prv-bridge-heading"><strong>Revenue bridge · PY to actual</strong><small>Price + volume + mix = revenue change · EUR</small></div><div class="prv-bridge-columns" role="list" aria-label="Source-reconciled price volume mix bridge">${columns}</div><button class="prv-text-link" data-prv-source="price_volume_mix.csv">Trace price-volume-mix source <span aria-hidden="true">↗</span></button></div>`;
  }
  function page(data,selection){
    const review=scope(data.performance_review||[],selection),actions=scope(data.management_actions||[],selection);
    const adverse=review.filter(row=>!row.favorable).sort((a,b)=>Number(b.materiality_pct)-Number(a.materiality_pct));
    const activeActions=actions.filter(active),carried=activeActions.filter(row=>Number(row.carry_forward_months)>0),overdue=activeActions.filter(row=>row.overdue===true||row.overdue==='True');
    const metrics=[['Revenue','Revenue vs budget'],['EBIT','EBIT vs budget'],['FY EBIT outlook','FY EBIT vs budget']].map(([metric,label])=>scoreCard(review.find(row=>row.metric===metric),label)).filter(Boolean);
    const status=[
      statusCard('Adverse signals',adverse.length,`${review.length} reviewed drivers`,'drivers'),
      statusCard('Active actions',activeActions.length,`${activeActions.filter(row=>row.priority==='P1').length} P1`,'actions'),
      statusCard('In progress',activeActions.filter(row=>row.status==='In Progress'||row.status==='In progress').length,'Owned active actions','actions'),
      statusCard('Overdue',overdue.length,`${overdue.filter(row=>row.escalation_level==='Executive').length} executive escalations`,'actions'),
      statusCard('Carry-forward',carried.length,carried.length?`Oldest ${Math.max(...carried.map(row=>Number(row.carry_forward_months)||0))} months`:'No aged actions','actions'),
      statusCard('Closed',actions.filter(row=>row.status==='Closed').length,'Closure evidence retained','actions'),
      statusCard('Cancelled',actions.filter(row=>row.status==='Cancelled').length,'Decision evidence retained','actions')
    ].join('');
    const narrative=adverse.slice(0,2).map(row=>`<button class="prv-signal" data-prv-observation="${esc(row.review_id)}"><span class="prv-severity">${esc(row.severity||'Review')}</span><strong>${esc(row.headline)}</strong><span>${esc(row.explanation)}</span><small>${esc(row.source_dataset)} · ${esc(row.comparison)} <span aria-hidden="true">↗</span></small></button>`).join('')||'<p class="prv-empty">No adverse signals in this selected scope.</p>';
    const sources=[...new Set(review.map(row=>row.source_dataset))].map(source=>({source,count:review.filter(row=>row.source_dataset===source).length}));
    const max=Math.max(1,...sources.map(row=>row.count));
    const coverage=sources.map(row=>`<button class="prv-source-row" data-prv-source="${esc(row.source)}" title="Inspect ${esc(row.source)} observations"><span>${esc(row.source)}</span><i aria-hidden="true"><b style="width:${(row.count/max*100).toFixed(2)}%"></b></i><strong>${row.count}</strong><span class="prv-arrow" aria-hidden="true">›</span></button>`).join('');
    const visual=bridge(review,data,selection);
    return `<article class="prv-overview" aria-label="Monthly performance review">
      <section class="prv-panel prv-score"><header><h2>Financial scorecard <small>vs budget</small></h2><button class="prv-text-link" data-prv-guide>How to read this <span aria-hidden="true">ⓘ</span></button></header><div class="prv-score-grid">${metrics.join('')}</div></section>
      <section class="prv-panel prv-actions" aria-label="Close and actions"><header><h2>Close and actions</h2><div class="prv-action-links"><button class="prv-text-link" data-prv-statuses>All statuses</button><button class="prv-text-link" data-prv-route="register"><span class="prv-register-long">Open </span>register <span aria-hidden="true">↗</span></button></div></header><div class="prv-status-grid">${status}</div></section>
      <section class="prv-panel prv-story ${visual?'':'prv-story-only'}"><header><div><h2>What changed and why it matters</h2><p>${adverse[0]?`Top adverse signal: ${esc(adverse[0].metric)}`:'No material adverse signal'}</p></div><button class="prv-text-link" data-prv-route="drivers">View all drivers <span aria-hidden="true">↗</span></button></header><div class="prv-story-body"><div class="prv-signals">${narrative}</div>${visual}</div></section>
      <section class="prv-panel prv-coverage"><header><div><h2>Review coverage</h2><p>Reviewed observations by source · selected scope</p></div><button class="prv-text-link" data-prv-route="controls">Controls <span aria-hidden="true">↗</span></button></header><div class="prv-source-list">${coverage}</div><p class="prv-control-note">Review IDs, source values, variance arithmetic and required action coverage are enforced by release controls.</p></section>
    </article>`;
  }
  function mount(data,selection,reportState,render,dialog){
    const host=document.querySelector('.prv-overview');if(!host)return;
    const review=scope(data.performance_review||[],selection);
    host.querySelectorAll('[data-prv-observation]').forEach(button=>button.onclick=()=>{
      const row=review.find(item=>String(item.review_id)===button.dataset.prvObservation);if(!row)return;
      const fields=[['Metric',row.metric],['Assessment',row.favorable?'Favorable':'Adverse'],['Actual',row.unit==='EUR'?exact(row.actual_value):row.actual_value],['Benchmark',row.unit==='EUR'?exact(row.benchmark_value):row.benchmark_value],['Variance',row.unit==='EUR'?exact(row.variance):row.variance],['Comparison',row.comparison],['Source',row.source_dataset],['Review ID',row.review_id]];
      dialog(row.headline,`<p>${esc(row.explanation)}</p><dl class="row-detail">${fields.map(([key,value])=>`<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`);
    });
    host.querySelectorAll('[data-prv-source]').forEach(button=>button.onclick=()=>{
      const source=button.dataset.prvSource,rows=review.filter(row=>row.source_dataset===source);
      dialog(`${source} · source observations`,`<p>${rows.length} reviewed observation${rows.length===1?'':'s'} in the selected scope.</p><dl class="row-detail">${rows.map(row=>`<div><dt>${esc(row.metric)}</dt><dd>${esc(row.unit==='EUR'?exact(row.variance):row.variance)} · ${esc(row.comparison)} · ${esc(row.review_id)}</dd></div>`).join('')}</dl>`);
    });
    host.querySelector('[data-prv-guide]').onclick=()=>dialog('How to read the performance review','<p>Each financial scorecard compares a published Actual or full-year Outlook with its frozen Budget. Bars share a scale only within that one measure. The variance is Actual − Budget; the materiality note is the published review materiality, not a growth rate.</p><p>The Group revenue bridge is shown only when the published price, volume and mix effects reconcile to the actual prior-year change. All review observations, actions and source counts follow the selected reporting scope.</p>');
    host.querySelector('[data-prv-statuses]').onclick=()=>{
      const cells=[...host.querySelectorAll('.prv-status')];
      dialog('All review and action states',`<dl class="row-detail">${cells.map(cell=>`<div><dt>${esc(cell.querySelector('.kpi-label').firstChild?.textContent?.trim())}</dt><dd>${esc(cell.querySelector('.kpi-value')?.textContent?.trim())} · ${esc(cell.querySelector('.kpi-note')?.textContent?.trim())}</dd></div>`).join('')}</dl>`);
    };
    host.querySelectorAll('[data-prv-route]').forEach(button=>button.onclick=()=>{
      const route=button.dataset.prvRoute;
      if(route==='actions'){selection.view='action-execution';reportState.page=0;render();return;}
      if(route==='controls'){selection.view='data-journey';reportState.page=0;render();return;}
      if(route==='register'){
        const register=reportState.pages.findIndex(page=>page.title.includes('Management action register'));
        if(register>=0){reportState.page=register;render();return;}
      }
      const index=reportState.pages.findIndex(page=>page.title.includes('Driver scorecard'));
      if(index>=0){reportState.page=index;render();}
    });
  }
  root.PerformanceReviewVisual={page,mount,scope,bridge,amount};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.PerformanceReviewVisual;
})(globalThis);
