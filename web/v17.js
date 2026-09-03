function lifecycleScope(rows){
  const all=rows||[];
  if(state.entity==='all' && state.division==='all') return all.filter(r=>r.scope_level==='Group');
  if(state.entity!=='all' && state.division==='all') return all.filter(r=>r.scope_level==='Entity' && r.entity===state.entity);
  if(state.entity==='all' && state.division!=='all') return all.filter(r=>r.scope_level==='Division' && r.division===state.division);
  return all.filter(r=>r.scope_level==='Entity Division' && r.entity===state.entity && r.division===state.division);
}

function actionStatus(value){
  const name=safe(value);
  const cls=['Closed','Cancelled'].includes(name)?'value-pos':name==='In Progress'?'value-warn':'';
  return `<span class="${cls}">${name}</span>`;
}

function lifecycleTrend(){
  const rows=lifecycleScope(data.management_action_history||[]),months=[...new Set(rows.map(r=>r.snapshot_month))].sort();
  return months.map(month=>{
    const snapshot=rows.filter(r=>r.snapshot_month===month),active=snapshot.filter(r=>['Open','In Progress'].includes(r.status));
    return {month,active:active.length,overdue:active.filter(r=>r.overdue===true || r.overdue==='True').length,carry_forward:active.filter(r=>Number(r.carry_forward_months)>0).length,closed:snapshot.filter(r=>r.status==='Closed').length};
  });
}

const renderPerformanceReviewBeforeLifecycle=renderers['performance-review'];
renderers['performance-review']=function(){
  const base=renderPerformanceReviewBeforeLifecycle();
  const actions=lifecycleScope(data.management_actions||[]),active=actions.filter(r=>['Open','In Progress'].includes(r.status));
  const overdue=active.filter(r=>r.overdue===true || r.overdue==='True').sort((a,b)=>Number(b.overdue_months)-Number(a.overdue_months));
  const carried=active.filter(r=>Number(r.carry_forward_months)>0).sort((a,b)=>Number(b.carry_forward_months)-Number(a.carry_forward_months));
  const trend=lifecycleTrend();
  return base+`<div class="section-note" style="margin-top:14px"><strong>Management action lifecycle</strong> — stable action cycles persist across closes. Status, ownership, due dates, age, closure evidence and changes are reconciled to monthly snapshots.</div>
  <div class="kpi-grid">
    ${kpi('In progress',String(active.filter(r=>r.status==='In Progress').length),'Owned active actions')}
    ${kpi('Overdue',String(overdue.length),`${overdue.filter(r=>r.escalation_level==='Executive').length} executive escalations`)}
    ${kpi('Carry-forward',String(carried.length),carried.length?`Oldest ${Math.max(...carried.map(r=>Number(r.carry_forward_months)||0))} months`:'No aged actions')}
    ${kpi('Closed',String(actions.filter(r=>r.status==='Closed').length),'Closure evidence retained')}
    ${kpi('Cancelled',String(actions.filter(r=>r.status==='Cancelled').length),'Decision evidence retained')}
  </div>
  <div class="panel-grid">
    ${panel('Lifecycle trend','Monthly controlled snapshots',table(trend,[{key:'month',label:'Close month'},{key:'active',label:'Active',num:true},{key:'overdue',label:'Overdue',num:true},{key:'carry_forward',label:'Carry-forward',num:true},{key:'closed',label:'Closed',num:true}]),'span-5')}
    ${panel('Overdue and escalated actions','Priority increases with overdue age',table(overdue,[{key:'priority',label:'Priority',format:v=>priorityBadge(v)},{key:'trigger_metric',label:'Trigger'},{key:'owner_role',label:'Owner'},{key:'due_month',label:'Due'},{key:'overdue_months',label:'Months overdue',num:true},{key:'escalation_level',label:'Escalation'}]),'span-7')}
    ${panel('Persistent action register','Current state with source and closure evidence',table(actions,[{key:'priority',label:'Priority',format:v=>priorityBadge(v)},{key:'trigger_metric',label:'Trigger'},{key:'owner_role',label:'Owner'},{key:'opened_month',label:'Opened'},{key:'due_month',label:'Due'},{key:'age_months',label:'Age',num:true},{key:'status',label:'Status',format:v=>actionStatus(v)},{key:'escalation_level',label:'Escalation'},{key:'source_dataset',label:'Evidence source'},{key:'closure_evidence',label:'Closure evidence'}]),'span-12')}
  </div>`;
};

const renderExecutiveBeforeLifecycle=renderers.executive;
renderers.executive=function(){
  const base=renderExecutiveBeforeLifecycle(),group=lifecycleScope(data.management_actions||[]),active=group.filter(r=>['Open','In Progress'].includes(r.status)),overdue=active.filter(r=>r.overdue===true || r.overdue==='True');
  return base+`<div class="panel-grid" style="margin-top:14px">${panel('Action lifecycle','Persistent group commitments',metricRows([['Active',active.length],['Overdue',overdue.length],['Carry-forward',active.filter(r=>Number(r.carry_forward_months)>0).length],['Executive escalation',active.filter(r=>r.escalation_level==='Executive').length]]),'span-12')}</div>`;
};

const renderJourneyBeforeLifecycle=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeLifecycle()+`<div class="panel-grid">${panel('Action lifecycle controls','No duplicate, orphaned or unsubstantiated actions',`<div class="section-note">Current required signals reconcile to one active action key. Monthly action and review snapshots retain traceability. Terminal actions require dated closure or cancellation evidence, and every overdue action requires a management or executive escalation.</div>`,'span-12')}</div>`;
};
