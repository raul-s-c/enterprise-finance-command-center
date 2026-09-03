const sensitivityOrder=['Price +1%','Volume +1%','Industrial production -1%','Inflation +100 bps','Wage inflation +100 bps','Energy index +10%','Policy rate +100 bps','EUR strengthening +5%'];

function scopedSensitivity(){
  let rows=data.financial_sensitivity_detail||[];
  if(state.entity!=='all') rows=rows.filter(r=>r.entity===state.entity);
  if(state.division!=='all') rows=rows.filter(r=>r.division===state.division);
  const fields=['base_revenue','base_gross_profit','base_opex','revenue_impact','gross_profit_impact','opex_benefit','ebit_impact','interest_expense_impact','net_income_impact','ending_cash_impact','net_debt_impact'];
  const map=new Map();
  for(const r of rows){
    const x=map.get(r.shock)||{shock:r.shock,driver:r.driver,shock_display:r.shock_display};
    for(const field of fields) x[field]=(Number(x[field])||0)+(Number(r[field])||0);
    map.set(r.shock,x);
  }
  return [...map.values()].sort((a,b)=>sensitivityOrder.indexOf(a.shock)-sensitivityOrder.indexOf(b.shock));
}

function sourceCoverage(){
  const sources=data.sources?.macro_drivers||{};
  return Object.entries(sources).map(([driver,x])=>({driver,preferred_source:x.preferred_source,official_rows:x.official_rows,fallback_rows:x.fallback_rows,latest_official_month:x.latest_official_month||'—'}));
}

function latestMacro(){
  const latest=(data.macro_lineage||[]).filter(r=>r.observation_month===data.meta.end_month);
  const labels={inflation:'Inflation',industrial_index:'Industrial production',energy_index:'Energy index',policy_rate:'Policy rate',USD:'USD / EUR',JPY:'JPY / EUR',CNY:'CNY / EUR',CZK:'CZK / EUR'};
  return latest.map(r=>({...r,driver_label:labels[r.driver]||r.driver}));
}

function macroValue(value,row){
  if(row.unit==='Annual rate') return pct(value);
  if(row.unit==='EUR per currency unit') return num(value,5);
  return num(value,1);
}

function renderMacroSensitivities(){
  const sensitivities=scopedSensitivity(),latest=latestMacro(),coverage=sourceCoverage();
  const summary=data.financial_sensitivity_summary||[];
  const official=coverage.reduce((s,r)=>s+Number(r.official_rows||0),0),fallback=coverage.reduce((s,r)=>s+Number(r.fallback_rows||0),0);
  const inflation=latest.find(r=>r.driver==='inflation'),industrial=latest.find(r=>r.driver==='industrial_index'),energy=latest.find(r=>r.driver==='energy_index'),rate=latest.find(r=>r.driver==='policy_rate');
  return `<div class="section-note"><strong>Macro lineage and controlled sensitivities</strong> — official public observations replace deterministic values only for matching months. Every shock is standalone, directionally controlled and non-additive; the Base forecast remains unchanged.</div>
  <div class="kpi-grid">
    ${kpi('Official observations',String(official),`${fallback} deterministic fallbacks`)}
    ${kpi('Inflation',inflation?pct(inflation.value):'—',inflation?.status||'No close observation')}
    ${kpi('Industrial index',industrial?num(industrial.value,1):'—',industrial?.status||'No close observation')}
    ${kpi('Energy index',energy?num(energy.value,1):'—',energy?.status||'No close observation')}
    ${kpi('Policy rate',rate?pct(rate.value):'—',rate?.status||'No close observation')}
  </div>
  <div class="panel-grid">
    ${panel('CFO sensitivity matrix','Standalone 12-month Base exposure; never sum shocks',table(sensitivities,[
      {key:'shock',label:'Shock'},{key:'revenue_impact',label:'Revenue',num:true,format:v=>signed(v)},
      {key:'gross_profit_impact',label:'Gross profit',num:true,format:v=>signed(v)},
      {key:'opex_benefit',label:'OPEX benefit',num:true,format:v=>signed(v)},
      {key:'ebit_impact',label:'EBIT',num:true,format:v=>signed(v)},
      {key:'net_income_impact',label:'Net income',num:true,format:v=>signed(v)},
      {key:'ending_cash_impact',label:'Ending cash',num:true,format:v=>signed(v)},
      {key:'net_debt_impact',label:'Net debt',num:true,format:v=>signed(v)}
    ]),'span-12')}
    ${panel('Close-month macro observations','Exact value and source used by the operating model',table(latest,[
      {key:'driver_label',label:'Driver'},{key:'value',label:'Value',num:true,format:(v,r)=>macroValue(v,r)},
      {key:'status',label:'Status',format:v=>`<span class="${v==='Official'?'value-pos':'value-warn'}">${safe(v)}</span>`},
      {key:'source',label:'Applied source'},{key:'official_source',label:'Preferred source'}
    ]),'span-7')}
    ${panel('Source coverage','Rolling 36-month lineage',table(coverage,[
      {key:'driver',label:'Driver'},{key:'official_rows',label:'Official',num:true},
      {key:'fallback_rows',label:'Fallback',num:true},{key:'latest_official_month',label:'Latest official'}
    ]),'span-5')}
    ${panel('Group covenant sensitivity','Covenant deltas remain group measures',table(summary,[
      {key:'shock',label:'Shock'},{key:'net_leverage_delta',label:'Net leverage delta',num:true,format:v=>num(v,3)},
      {key:'interest_coverage_delta',label:'Interest coverage delta',num:true,format:v=>num(v,2)}
    ]),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='macro-sensitivities')){
  const planIndex=views.findIndex(v=>v[0]==='forecast');
  views.splice(planIndex>=0?planIndex:3,0,['macro-sensitivities','Macro & Sensitivities','Official driver lineage and controlled financial exposure.']);
}
renderers['macro-sensitivities']=renderMacroSensitivities;

const renderJourneyBeforeMacro=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeMacro()+`<div class="panel-grid">${panel('Macro and sensitivity controls','Observed sources, explicit fallback and non-additive shocks',`<div class="section-note">Each driver-month records the applied value, official source, URL and Official/Fallback status. Sensitivity detail reconciles to the group matrix, EBIT equals Gross Profit impact plus OPEX benefit, Ending Cash offsets Net Debt and directional controls reject counter-intuitive results.</div>`,'span-12')}</div>`;
};
