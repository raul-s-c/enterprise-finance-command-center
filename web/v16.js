function performanceScope(rows){
  const all=rows||[];
  if(state.entity==='all' && state.division==='all') return all.filter(r=>r.scope_level==='Group');
  if(state.entity!=='all' && state.division==='all') return all.filter(r=>r.scope_level==='Entity' && r.entity===state.entity);
  if(state.entity==='all' && state.division!=='all') return all.filter(r=>r.scope_level==='Division' && r.division===state.division);
  return all.filter(r=>r.scope_level==='Entity Division' && r.entity===state.entity && r.division===state.division);
}

function reviewValue(value,unit){
  const v=Number(value)||0;
  if(unit==='Percent') return pct(v);
  if(unit==='FTE') return num(v,1);
  if(unit==='EUR/FTE') return `${eur.format(v)} / FTE`;
  return eur.format(v);
}

function reviewSigned(value,unit){
  const v=Number(value)||0;
  const rendered=unit==='Percent'?`${v>=0?'+':''}${pct(v)}`:unit==='FTE'?`${v>=0?'+':''}${num(v,1)}`:eur.format(v);
  return `<span class="${v>=0?'value-pos':'value-neg'}">${rendered}</span>`;
}

function reviewScopeLabel(row){
  if(row.scope_level==='Group') return 'Group';
  if(row.scope_level==='Entity') return row.entity;
  if(row.scope_level==='Division') return row.division;
  return `${row.entity} / ${row.division}`;
}

function severityBadge(value){
  const name=safe(value)||'Low';
  return `<span class="review-badge severity-${name.toLowerCase()}">${name}</span>`;
}

function priorityBadge(value){
  const name=safe(value);
  return `<span class="review-badge priority-${name.toLowerCase()}">${name}</span>`;
}

function renderPerformanceReview(){
  const review=performanceScope(data.performance_review||[]);
  const actions=performanceScope(data.management_actions||[]);
  const adverse=review.filter(r=>!r.favorable).sort((a,b)=>Number(b.materiality_pct)-Number(a.materiality_pct));
  const favorable=review.filter(r=>r.favorable).sort((a,b)=>Number(b.materiality_pct)-Number(a.materiality_pct));
  const narrative=[...adverse,...favorable].slice(0,6);
  const metric=name=>review.find(r=>r.metric===name);
  const revenue=metric('Revenue');
  const ebit=metric('EBIT');
  const outlook=metric('FY EBIT outlook');
  const top=adverse[0];
  const sourceCounts=[...new Set(review.map(r=>r.source_dataset))].map(source=>({source,count:review.filter(r=>r.source_dataset===source).length}));
  return `<div class="section-note"><strong>Monthly performance review</strong> — deterministic explanations and actions generated only from reconciled close datasets. Severity reflects variance materiality; every P1/P2 action retains its source metric, scope, owner and due month.</div>
  <div class="kpi-grid">
    ${kpi('Revenue vs budget',revenue?reviewSigned(revenue.variance,revenue.unit):'-',revenue?`${pct(Number(revenue.materiality_pct))} materiality`:'Not available')}
    ${kpi('EBIT vs budget',ebit?reviewSigned(ebit.variance,ebit.unit):'-',ebit?`${pct(Number(ebit.materiality_pct))} materiality`:'Not available')}
    ${kpi('FY EBIT vs budget',outlook?reviewSigned(outlook.variance,outlook.unit):'-',outlook?'Latest full-year outlook':'Group scope only')}
    ${kpi('Adverse signals',String(adverse.length),`${review.length} reviewed drivers`)}
    ${kpi('Open actions',String(actions.filter(r=>r.status==='Open').length),`${actions.filter(r=>r.priority==='P1').length} P1`)}
  </div>
  <div class="panel-grid">
    ${panel('CFO performance narrative',top?`Top adverse signal: ${top.metric}`:'No material adverse signal',`<div class="review-list">${narrative.map(r=>`<div class="review-item ${r.favorable?'favorable':'adverse'}"><div class="review-item-head"><span>${severityBadge(r.severity)} <strong>${safe(r.headline)}</strong></span><span>${reviewScopeLabel(r)}</span></div><div class="review-item-detail">${safe(r.explanation)}</div><div class="review-source">${safe(r.source_dataset)} · ${safe(r.comparison)}</div></div>`).join('')||'<div class="empty">No review observations for this selection.</div>'}</div>`,'span-7')}
    ${panel('Review coverage','Source datasets in the selected scope',`${metricRows(sourceCounts.map(r=>[r.source,`${r.count} observations`]))}<div class="section-note review-control-note">Review IDs, source values, variance arithmetic and required action coverage are enforced by release controls.</div>`,'span-5')}
    ${panel('Driver scorecard','Actual, benchmark and source-tied variance',table(review,[
      {key:'category',label:'Category'},{key:'metric',label:'Metric'},{key:'comparison',label:'Comparison'},
      {key:'actual_value',label:'Actual',num:true,format:(v,r)=>reviewValue(v,r.unit)},
      {key:'benchmark_value',label:'Benchmark',num:true,format:(v,r)=>reviewValue(v,r.unit)},
      {key:'variance',label:'Variance',num:true,format:(v,r)=>reviewSigned(v,r.unit)},
      {key:'favorable',label:'Assessment',format:v=>v?'<span class="value-pos">Favorable</span>':'<span class="value-neg">Adverse</span>'},
      {key:'severity',label:'Severity',format:v=>severityBadge(v)},{key:'source_dataset',label:'Source'}
    ]),'span-12')}
    ${panel('Management action register','Only material adverse signals become owned actions',table(actions,[
      {key:'priority',label:'Priority',format:v=>priorityBadge(v)},{key:'trigger_metric',label:'Trigger'},
      {key:'scope_level',label:'Scope',format:(v,r)=>reviewScopeLabel(r)},{key:'owner_role',label:'Owner'},
      {key:'action',label:'Management action'},{key:'due_month',label:'Due'},{key:'status',label:'Status'},
      {key:'source_dataset',label:'Evidence'}
    ]),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='performance-review')) views.splice(1,0,['performance-review','Performance Review','Close variance, source-tied explanations and owned management actions.']);
renderers['performance-review']=renderPerformanceReview;

const renderExecutiveBeforeReview=renderers.executive;
renderers.executive=function(){
  const base=renderExecutiveBeforeReview();
  const groupReview=(data.performance_review||[]).filter(r=>r.scope_level==='Group' && !r.favorable).sort((a,b)=>Number(b.materiality_pct)-Number(a.materiality_pct)).slice(0,4);
  const groupActions=(data.management_actions||[]).filter(r=>r.scope_level==='Group' && r.status==='Open').sort((a,b)=>a.priority.localeCompare(b.priority)).slice(0,4);
  return base+`<div class="panel-grid review-executive-extension">
    ${panel('Close priorities','Highest-materiality adverse signals',table(groupReview,[{key:'metric',label:'Metric'},{key:'variance',label:'Variance',num:true,format:(v,r)=>reviewSigned(v,r.unit)},{key:'severity',label:'Severity',format:v=>severityBadge(v)},{key:'source_dataset',label:'Source'}]),'span-6')}
    ${panel('Management commitments','Open group actions',table(groupActions,[{key:'priority',label:'Priority',format:v=>priorityBadge(v)},{key:'trigger_metric',label:'Trigger'},{key:'owner_role',label:'Owner'},{key:'due_month',label:'Due'}]),'span-6')}
  </div>`;
};

const renderJourneyBeforeReview=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeReview()+`<div class="panel-grid">${panel('Monthly performance review','Reconciled close → variance → explanation → action',`<div class="section-note">The review engine compares actual performance with Budget, prior year, prior month, constant-currency results and the latest full-year outlook. It ranks materiality, writes deterministic explanations, and creates owned P1/P2 actions only for material adverse signals. Release controls fail if a source value drifts, an action loses its evidence, or a required action is missing.</div>`,'span-12')}</div>`;
};
