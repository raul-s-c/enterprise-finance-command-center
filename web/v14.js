function workforceScope(rows){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'entity'))) out=out.filter(r=>r.entity===state.entity);
  if(state.division!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'division'))) out=out.filter(r=>r.division===state.division);
  return out;
}

function workforceBlock(){
  const detail=workforceScope(data.workforce_detail||[]);
  const group=data.workforce_summary||[];
  const latestGroup=latest(group);
  const selected=detail.reduce((a,r)=>{
    a.opening+=Number(r.opening_fte)||0;
    a.hires+=Number(r.hires)||0;
    a.attrition+=Number(r.attrition)||0;
    a.ending+=Number(r.ending_fte)||0;
    a.avg+=Number(r.average_fte)||0;
    a.personnel+=Number(r.personnel_cost)||0;
    a.revenue+=Number(r.revenue)||0;
    return a;
  },{opening:0,hires:0,attrition:0,ending:0,avg:0,personnel:0,revenue:0});
  const useSelected=state.entity!=='all'||state.division!=='all';
  const ending=useSelected?selected.ending:Number(latestGroup.ending_fte)||0;
  const hires=useSelected?selected.hires:Number(latestGroup.hires)||0;
  const attrition=useSelected?selected.attrition:Number(latestGroup.attrition)||0;
  const personnel=useSelected?selected.personnel:Number(latestGroup.personnel_cost)||0;
  const revenue=useSelected?selected.revenue:Number(latestGroup.revenue)||0;
  const avg=useSelected?selected.avg:Number(latestGroup.average_fte)||0;
  return `<div class="section-note"><strong>Workforce economics</strong> — aggregated finance planning only. Headcount follows lagged demand, attrition, hiring and productivity; payroll is paid directly in cash and is excluded from Trade AP.</div>
  <div class="kpi-grid">
    ${kpi('Ending FTE',num(ending,1))}
    ${kpi('Monthly hires',num(hires,1))}
    ${kpi('Monthly attrition',num(attrition,1))}
    ${kpi('Personnel cost',eur.format(personnel))}
    ${kpi('Revenue / FTE',eur.format(avg?revenue/avg:0))}
    ${kpi('Personnel cost / revenue',pct(revenue?personnel/revenue:0))}
  </div>
  <div class="panel-grid">
    ${panel('Workforce by function','Latest close; no employee-level synthetic data',table(detail,[
      {key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'function',label:'Function'},
      {key:'opening_fte',label:'Opening FTE',num:true,format:v=>num(v,1)},
      {key:'hires',label:'Hires',num:true,format:v=>num(v,1)},
      {key:'attrition',label:'Attrition',num:true,format:v=>num(v,1)},
      {key:'ending_fte',label:'Ending FTE',num:true,format:v=>num(v,1)},
      {key:'personnel_cost',label:'Personnel cost',num:true,format:v=>eur.format(v)},
      {key:'revenue_per_fte',label:'Revenue / FTE',num:true,format:v=>eur.format(v)}
    ]),'span-8')}
    ${panel('FTE trend','Group workforce capacity',bars(group.slice(-24),'ending_fte'),'span-4')}
  </div>`;
}

const businessDriversBeforeWorkforce=renderers['business-drivers'];
renderers['business-drivers']=function(){
  return businessDriversBeforeWorkforce()+workforceBlock();
};

const forecastBeforeWorkforce=renderers.forecast;
renderers.forecast=function(){
  const base=forecastBeforeWorkforce();
  let rows=workforceScope(data.workforce_forecast||[]).filter(r=>r.scenario==='Base'&&Number(r.horizon_month)<=12);
  const byMonth=new Map();
  for(const r of rows){
    const x=byMonth.get(r.month)||{month:r.month,fte:0,target:0,hires:0,attrition:0,personnel:0,non_people:0,opex:0};
    x.fte+=Number(r.workforce_fte_forecast)||0;x.target+=Number(r.workforce_target_fte)||0;x.hires+=Number(r.workforce_hires_forecast)||0;x.attrition+=Number(r.workforce_attrition_forecast)||0;x.personnel+=Number(r.personnel_cost_forecast)||0;x.non_people+=Number(r.non_people_opex_forecast)||0;x.opex+=Number(r.opex_forecast)||0;
    byMonth.set(r.month,x);
  }
  const plan=[...byMonth.values()].sort((a,b)=>a.month.localeCompare(b.month));
  const totalPersonnel=plan.reduce((s,r)=>s+r.personnel,0),totalHires=plan.reduce((s,r)=>s+r.hires,0),last=plan.at(-1)||{};
  return base+`<div class="section-note"><strong>Workforce plan:</strong> forecast OPEX now combines projected personnel cost and non-people OPEX instead of applying a single OPEX percentage to revenue.</div><div class="kpi-grid">${kpi('12M personnel cost',eur.format(totalPersonnel))}${kpi('12M planned hires',num(totalHires,1))}${kpi('12M ending FTE',num(last.fte||0,1))}${kpi('12M target FTE',num(last.target||0,1))}</div><div class="panel-grid">${panel('Base workforce plan','FTE and cost consequences of the operating forecast',table(plan,[{key:'month',label:'Month'},{key:'fte',label:'Ending FTE',num:true,format:v=>num(v,1)},{key:'target',label:'Target FTE',num:true,format:v=>num(v,1)},{key:'hires',label:'Hires',num:true,format:v=>num(v,1)},{key:'attrition',label:'Attrition',num:true,format:v=>num(v,1)},{key:'personnel',label:'Personnel',num:true,format:v=>eur.format(v)},{key:'non_people',label:'Non-people OPEX',num:true,format:v=>eur.format(v)},{key:'opex',label:'Total OPEX',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const pnlBeforeWorkforce=renderers.pnl;
renderers.pnl=function(){
  const base=pnlBeforeWorkforce();
  const workforce=latest(data.workforce_summary||[]);
  const actual=(data.actual||[]).find(r=>r.month===data.meta.end_month)||{};
  const personnel=Number(workforce.personnel_cost)||0;
  const totalOpex=Number(actual.opex)||0;
  return base+`<div class="panel-grid">${panel('OPEX composition','Latest close',metricRows([['Personnel cost',eur.format(personnel)],['Non-people OPEX',eur.format(Math.max(totalOpex-personnel,0))],['Total OPEX',eur.format(totalOpex)],['Personnel share of OPEX',pct(totalOpex?personnel/totalOpex:0)]]),'span-12')}</div>`;
};

const journeyBeforeWorkforce=renderers['data-journey'];
renderers['data-journey']=function(){
  return journeyBeforeWorkforce()+`<div class="panel-grid">${panel('Workforce cost planning','Demand-driven capacity and payroll economics',`<div class="section-note">Workforce is modeled only at Month × Entity × Division × Function. Opening FTE minus attrition plus hires equals Ending FTE. Payroll and recruitment costs are allocated to products/customers for profitability, but payroll is paid directly through cash and never creates Trade AP. The rolling forecast projects FTE and personnel cost separately from external OPEX.</div>`,'span-12')}</div>`;
};
