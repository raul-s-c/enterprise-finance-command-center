function executionScope(rows){
  const all=rows||[];
  if(state.entity==='all' && state.division==='all') return all;
  if(state.entity!=='all' && state.division==='all') return all.filter(r=>r.scope_level==='Entity' && r.entity===state.entity);
  if(state.entity==='all' && state.division!=='all') return all.filter(r=>r.scope_level==='Division' && r.division===state.division);
  return all.filter(r=>r.scope_level==='Entity Division' && r.entity===state.entity && r.division===state.division);
}

function executionStatus(value){
  const name=safe(value),positive=['Benefits validated'].includes(name),warning=['Implementing','Benefits tracking'].includes(name);
  return `<span class="${positive?'value-pos':warning?'value-warn':''}">${name}</span>`;
}

function scopedActionBridge(){
  let rows=(data.management_action_forecast_bridge||[]).filter(r=>r.scenario==='Base' && Number(r.horizon_month)<=12);
  if(state.entity!=='all') rows=rows.filter(r=>r.entity===state.entity);
  if(state.division!=='all') rows=rows.filter(r=>r.division===state.division);
  const map=new Map();
  for(const r of rows){
    const x=map.get(r.month)||{month:r.month,horizon_month:r.horizon_month,scenario:r.scenario,action_revenue_impact:0,action_gross_profit_impact:0,action_opex_impact:0,action_ebit_impact:0,active_action_count:0};
    for(const key of ['action_revenue_impact','action_gross_profit_impact','action_opex_impact','action_ebit_impact']) x[key]+=Number(r[key])||0;
    x.active_action_count=Math.max(x.active_action_count,Number(r.active_action_count)||0);map.set(r.month,x);
  }
  return [...map.values()].sort((a,b)=>a.month.localeCompare(b.month));
}

function scopedActualImpact(){
  let rows=data.management_action_actual_impact||[];
  if(state.entity!=='all') rows=rows.filter(r=>r.entity===state.entity);
  if(state.division!=='all') rows=rows.filter(r=>r.division===state.division);
  const map=new Map();
  for(const r of rows){
    const x=map.get(r.month)||{month:r.month,action_revenue_impact:0,action_gross_profit_impact:0,action_opex_impact:0,action_ebit_impact:0,active_action_count:0};
    for(const key of ['action_revenue_impact','action_gross_profit_impact','action_opex_impact','action_ebit_impact']) x[key]+=Number(r[key])||0;
    x.active_action_count=Math.max(x.active_action_count,Number(r.active_action_count)||0);map.set(r.month,x);
  }
  return [...map.values()].sort((a,b)=>a.month.localeCompare(b.month));
}

function renderActionExecution(){
  const summary=data.management_action_execution_summary||{};
  const plans=executionScope(data.management_action_plans||[]);
  const benefits=executionScope((data.management_action_benefits||[]).filter(r=>r.snapshot_month===data.meta.end_month));
  const bridge=scopedActionBridge();
  const actual=scopedActualImpact().slice(-12);
  const operational=plans.filter(r=>Number(r.price_uplift_pct)+Number(r.volume_uplift_pct)+Number(r.variable_cost_reduction_pct)+Number(r.opex_reduction_pct)>0);
  return `<div class="section-note"><strong>Action execution and benefits realization</strong> — approved actions change future operating drivers from their effective month. Directional trigger improvements remain non-additive; only the operating and forecast impact bridges are additive portfolio evidence.</div>
  <div class="kpi-grid">
    ${kpi('Approved plans',String(plans.length),`${operational.length} operating interventions`)}
    ${kpi('Gross plan cases',eur.format(plans.reduce((s,r)=>s+Number(r.expected_benefit_eur||0),0)),'Non-additive action cases')}
    ${kpi('12M Revenue impact',eur.format(bridge.reduce((s,r)=>s+Number(r.action_revenue_impact||0),0)),'Selected-scope Base bridge')}
    ${kpi('12M EBIT impact',eur.format(bridge.reduce((s,r)=>s+Number(r.action_ebit_impact||0),0)),'Selected-scope additive bridge')}
    ${kpi('Current actual impact',eur.format(summary.latest_additive_actual_ebit_impact||0),'Zero before effective month')}
  </div>
  <div class="panel-grid">
    ${panel('Execution portfolio','One controlled plan per action cycle',table(plans,[
      {key:'priority',label:'Priority',format:v=>priorityBadge(v)},{key:'intervention_type',label:'Intervention'},
      {key:'primary_driver',label:'Driver'},{key:'owner_role',label:'Owner'},{key:'effective_month',label:'Effective'},
      {key:'target_month',label:'Target'},{key:'execution_status',label:'Execution',format:v=>executionStatus(v)},
      {key:'expected_benefit_eur',label:'Gross case',num:true,format:v=>eur.format(v)}
    ]),'span-12')}
    ${panel('Base forecast action bridge','Incremental impact after the current close',table(bridge,[
      {key:'month',label:'Month'},{key:'active_action_count',label:'Actions',num:true},
      {key:'action_revenue_impact',label:'Revenue',num:true,format:v=>signed(v)},
      {key:'action_gross_profit_impact',label:'Gross profit',num:true,format:v=>signed(v)},
      {key:'action_opex_impact',label:'OPEX benefit',num:true,format:v=>signed(v)},
      {key:'action_ebit_impact',label:'EBIT',num:true,format:v=>signed(v)}
    ]),'span-7')}
    ${panel('Directional benefit tracking','Trigger movement; deliberately not summed',table(benefits,[
      {key:'trigger_metric',label:'Trigger'},{key:'execution_status',label:'Execution',format:v=>executionStatus(v)},
      {key:'baseline_metric_value',label:'Baseline',num:true,format:(v,r)=>r.benefit_unit==='EUR'?eur.format(v):num(v,3)},
      {key:'current_metric_value',label:'Current',num:true,format:(v,r)=>r.benefit_unit==='EUR'?eur.format(v):num(v,3)},
      {key:'observed_metric_improvement',label:'Improvement',num:true,format:(v,r)=>r.benefit_unit==='EUR'?signed(v):num(v,3)}
    ]),'span-5')}
    ${panel('Actual additive impact','Recognized only after effective dates',table(actual,[
      {key:'month',label:'Month'},{key:'active_action_count',label:'Actions',num:true},
      {key:'action_revenue_impact',label:'Revenue',num:true,format:v=>signed(v)},
      {key:'action_gross_profit_impact',label:'Gross profit',num:true,format:v=>signed(v)},
      {key:'action_opex_impact',label:'OPEX benefit',num:true,format:v=>signed(v)},
      {key:'action_ebit_impact',label:'EBIT',num:true,format:v=>signed(v)}
    ]),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='action-execution')) views.splice(2,0,['action-execution','Action Execution','Approved interventions, forecast impact and realized benefits.']);
renderers['action-execution']=renderActionExecution;

const renderExecutiveBeforeExecution=renderers.executive;
renderers.executive=function(){
  const base=renderExecutiveBeforeExecution(),summary=data.management_action_execution_summary||{};
  return base+`<div class="panel-grid" style="margin-top:14px">${panel('Benefits realization','Approved action portfolio',metricRows([
    ['Operationalized plans',summary.operationalized_plans||0],['Governance-only plans',summary.governance_only_plans||0],
    ['Base 12M EBIT impact',eur.format(summary.base_12m_action_ebit_impact||0)],['Current actual EBIT impact',eur.format(summary.latest_additive_actual_ebit_impact||0)]
  ]),'span-12')}</div>`;
};

const renderJourneyBeforeExecution=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeExecution()+`<div class="panel-grid">${panel('Action execution controls','No plugs and no double-counted realization',`<div class="section-note">Every action cycle has one approved plan, dated evidence and a controlled driver profile. Interventions begin only after approval. Directional trigger improvements are explicitly non-additive; portfolio impact comes only from operating and forecast bridges that flow through the existing accounting and three-statement controls.</div>`,'span-12')}</div>`;
};
