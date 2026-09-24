/* Source-tied action execution visuals. Gross cases are never treated as additive impact. */
(function(root){
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const amount=value=>new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(Number(value)||0);
  const compact=value=>Math.abs(Number(value)||0)<1e6?`€${new Intl.NumberFormat('en-GB',{maximumFractionDigits:0}).format((Number(value)||0)/1e3)}k`:`€${new Intl.NumberFormat('en-GB',{maximumFractionDigits:1,minimumFractionDigits:1}).format((Number(value)||0)/1e6)}m`;
  const monthLabel=value=>new Intl.DateTimeFormat('en-GB',{month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(`${value}-01T00:00:00Z`));
  const stages=['Approved','Implementing','Benefits tracking','Benefits validated'];

  function portfolio(plans,fullTable){
    const rows=plans||[],labels=[...stages,...new Set(rows.map(row=>row.execution_status||'Unspecified').filter(stage=>!stages.includes(stage)))],counts=labels.map(stage=>rows.filter(row=>(row.execution_status||'Unspecified')===stage).length);
    const leaders=[...rows].sort((a,b)=>String(a.priority).localeCompare(String(b.priority))||String(a.effective_month).localeCompare(String(b.effective_month))).slice(0,3);
    return `<div class="aev-portfolio action-execution-visual">
      <div class="aev-stage-list" aria-label="Approved plan count by execution stage">${labels.map((stage,index)=>`<div class="aev-stage"><span>${esc(stage)}</span><div class="aev-stage-track"><i style="width:${rows.length?counts[index]/rows.length*100:0}%"></i></div><strong>${counts[index]}</strong></div>`).join('')}</div>
      <div class="aev-list-heading"><strong>Priority actions</strong><span>${Math.min(3,rows.length)} of ${rows.length} scoped plans</span></div>
      <div class="aev-plan-list">${leaders.map(row=>`<details class="aev-plan"><summary><b>${esc(row.priority)}</b><span><strong>${esc(row.intervention_type)}</strong><small>${esc(row.primary_driver)} · ${esc(row.owner_role)}</small></span><em>${esc(row.effective_month)}</em></summary><div class="aev-plan-evidence"><p><b>Expected outcome:</b> ${esc(row.expected_outcome)}</p><p><b>Evidence:</b> ${esc(row.execution_evidence)}</p><p><b>Source review:</b> ${esc(row.source_review_id)}</p><p><b>Gross case, non-additive:</b> ${amount(row.expected_benefit_eur)}</p></div></details>`).join('')||'<p class="aev-empty">No approved plans in this scope.</p>'}</div>
      <details class="aev-records"><summary>View all ${rows.length} approved plans and source fields</summary>${fullTable}</details>
    </div>`;
  }

  function bridge(rows,fullTable){
    const records=rows||[];
    if(!records.length)return `<div class="action-execution-visual aev-empty">No additive Base forecast impact in this scope.<details class="aev-records"><summary>View source records</summary>${fullTable}</details></div>`;
    const values=records.map(row=>Number(row.action_ebit_impact)||0),max=Math.max(1,...values.map(Math.abs));
    const hasNegative=values.some(value=>value<0),zero=hasNegative?99:143,range=hasNegative?64:103;
    const selected=records[0];
    const bars=records.map((row,index)=>{const value=values[index],height=Math.abs(value)/max*range,x=52+index*44,y=value>=0?zero-height:zero;
      return `<g class="aev-bar ${index===0?'selected':''}" role="button" tabindex="0" aria-label="${esc(row.month)} Base EBIT impact ${amount(value)}" aria-pressed="${index===0}" data-aev-month="${esc(row.month)}"><rect x="${x}" y="${y.toFixed(2)}" width="27" height="${Math.max(1,height).toFixed(2)}" class="${value<0?'aev-bar-negative':'aev-bar-positive'}"><title>${esc(row.month)} · EBIT ${amount(value)}</title></rect><text x="${x+13.5}" y="181" text-anchor="middle">${esc(row.month.slice(5))}</text></g>`;}).join('');
    return `<div class="aev-bridge action-execution-visual"><div class="aev-chart-caption"><span>Monthly additive EBIT impact · Base scenario</span><span>EUR · ${monthLabel(records[0].month)}–${monthLabel(records.at(-1).month)}</span></div>
      <svg class="aev-chart" viewBox="0 0 620 190" role="img" aria-label="${records.length}-month Base forecast action EBIT impact; select a month for source-tied values"><line x1="35" x2="590" y1="${zero}" y2="${zero}" class="aev-zero"/><text x="30" y="${zero+4}" text-anchor="end">0</text><line x1="35" x2="590" y1="${zero-range}" y2="${zero-range}" class="aev-grid"/><text x="30" y="${zero-range+4}" text-anchor="end">${compact(max)}</text>${bars}</svg>
      <div class="aev-selected" aria-live="polite"><strong data-aev-selected-month>${esc(selected.month)} · Base impact</strong><div><span>EBIT <b data-aev-ebit>${amount(selected.action_ebit_impact)}</b></span><span>Revenue <b data-aev-revenue>${amount(selected.action_revenue_impact)}</b></span><span>Active actions <b data-aev-count>${Number(selected.active_action_count)||0}</b></span></div></div>
      <script type="application/json" class="aev-bridge-data">${JSON.stringify(records.map(row=>({month:row.month,ebit:Number(row.action_ebit_impact)||0,revenue:Number(row.action_revenue_impact)||0,count:Number(row.active_action_count)||0}))).replace(/</g,'\\u003c')}</script>
      <details class="aev-records"><summary>View complete ${records.length}-month additive bridge</summary>${fullTable}</details></div>`;
  }

  function benefits(rows,fullTable){
    const records=rows||[],improving=records.filter(row=>Number(row.observed_metric_improvement)>0).length;
    const fmt=(value,unit)=>unit==='EUR'?amount(value):new Intl.NumberFormat('en-GB',{maximumFractionDigits:3}).format(Number(value)||0);
    return `<div class="aev-benefits action-execution-visual"><div class="aev-benefit-summary"><strong>${improving} of ${records.length}</strong><span>triggers improving at this close</span></div><p>Each trigger is compared with its own baseline. Different units and action cases are not summed.</p>
      <div class="aev-trigger-list">${records.slice(0,5).map(row=>`<div class="aev-trigger"><strong>${esc(row.trigger_metric)}</strong><span>${fmt(row.baseline_metric_value,row.benefit_unit)} <i aria-hidden="true">→</i> ${fmt(row.current_metric_value,row.benefit_unit)}</span><em>${Number(row.observed_metric_improvement)>0?'Improving':Number(row.observed_metric_improvement)<0?'Adverse':'Unchanged'}</em></div>`).join('')||'<p>No directional benefit records in this scope.</p>'}</div>
      <details class="aev-records"><summary>View all ${records.length} directional trigger records</summary>${fullTable}</details></div>`;
  }

  function actual(rows,plans,closeMonth,fullTable){
    const records=rows||[],current=records.at(-1),next=[...new Set((plans||[]).map(row=>row.effective_month).filter(month=>month>closeMonth))].sort()[0];
    const allZero=records.every(row=>Math.abs(Number(row.action_ebit_impact)||0)<.005);
    const max=Math.max(1,...records.map(row=>Math.abs(Number(row.action_ebit_impact)||0)));
    const historyGraphic=allZero?`<div class="aev-actual-zero" role="img" aria-label="${records.length} months of actual additive EBIT impact; all zero before effective dates"><span>0</span><i></i></div>`:`<svg class="aev-actual-bars" viewBox="0 0 500 88" role="img" aria-label="${records.length} months of actual additive EBIT impact"><line x1="20" x2="490" y1="44" y2="44" class="aev-zero"/>${records.map((row,index)=>{const value=Number(row.action_ebit_impact)||0,height=Math.abs(value)/max*32,x=27+index*(455/Math.max(1,records.length));return `<rect x="${x.toFixed(1)}" y="${(value>=0?44-height:44).toFixed(1)}" width="${Math.min(18,400/Math.max(1,records.length)).toFixed(1)}" height="${Math.max(1,height).toFixed(1)}" class="${value<0?'aev-bar-negative':'aev-bar-positive'}"><title>${esc(row.month)} · ${amount(value)}</title></rect>`;}).join('')}</svg>`;
    return `<div class="aev-actual action-execution-visual"><div class="aev-recognition"><div><small>Published close</small><strong>${esc(closeMonth)}</strong><span>${amount(current?.action_ebit_impact)} actual EBIT impact</span></div><i aria-hidden="true">→</i><div><small>Next plan effective</small><strong>${esc(next||'No future approval')}</strong><span>Impact recognized only after effective date</span></div></div>
      <div class="aev-actual-history"><div><strong>Actual additive EBIT impact</strong><span>${records.length} published months · EUR</span></div>${historyGraphic}<p>${allZero?'No action impact has entered actuals yet. The published close precedes the approved effective month.':'Recognized impact is sourced from the actual impact bridge; inspect monthly values below.'}</p></div>
      <details class="aev-records"><summary>View complete actual impact by month</summary>${fullTable}</details></div>`;
  }

  function selectMonth(target){
    const bar=target.closest('[data-aev-month]');if(!bar)return;
    const visual=bar.closest('.aev-bridge');if(!visual)return;
    const records=JSON.parse(visual.querySelector('.aev-bridge-data').textContent||'[]');
    const row=records.find(item=>item.month===bar.dataset.aevMonth);if(!row)return;
    for(const item of visual.querySelectorAll('[data-aev-month]')){const selected=item===bar;item.classList.toggle('selected',selected);item.setAttribute('aria-pressed',String(selected));}
    visual.querySelector('[data-aev-selected-month]').textContent=`${row.month} · Base impact`;
    visual.querySelector('[data-aev-ebit]').textContent=amount(row.ebit);
    visual.querySelector('[data-aev-revenue]').textContent=amount(row.revenue);
    visual.querySelector('[data-aev-count]').textContent=String(row.count);
  }
  if(root.document){
    document.addEventListener('click',event=>selectMonth(event.target));
    document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.closest('[data-aev-month]')){event.preventDefault();selectMonth(event.target);}});
  }
  root.FinanceActionVisual={portfolio,bridge,benefits,actual};
})(globalThis);
