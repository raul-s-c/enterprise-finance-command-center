function scopedPlan(rows){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'entity'))) out=out.filter(r=>r.entity===state.entity);
  if(state.division!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'division'))) out=out.filter(r=>r.division===state.division);
  return out;
}

function sumPlan(rows,key){return (rows||[]).reduce((s,r)=>s+(Number(r[key])||0),0)}
function variancePct(actual,budget){return budget?(actual/budget-1):0}

function aggregateBudgetMonthly(rows){
  const map=new Map();
  for(const r of rows||[]){
    const x=map.get(r.month)||{month:r.month,revenue_budget:0,ebit_budget:0,revenue:0,ebit:0,revenue_variance:0,ebit_variance:0};
    for(const k of ['revenue_budget','ebit_budget','revenue','ebit','revenue_variance','ebit_variance']) x[k]+=Number(r[k])||0;
    map.set(r.month,x);
  }
  return [...map.values()].sort((a,b)=>a.month.localeCompare(b.month));
}

function aggregateBridgeByDivision(rows){
  const map=new Map();
  const numeric=['fy_budget_revenue','fy_budget_ebit','ytd_budget_revenue','ytd_actual_revenue','ytd_revenue_variance','ytd_budget_ebit','ytd_actual_ebit','ytd_ebit_variance','latest_fy_revenue','latest_fy_revenue_vs_budget','latest_fy_ebit','latest_fy_ebit_vs_budget','fc_1_fy_revenue','fc_3_fy_revenue','fc_6_fy_revenue'];
  for(const r of rows||[]){
    const x=map.get(r.division)||{division:r.division};
    for(const k of numeric)x[k]=(Number(x[k])||0)+(Number(r[k])||0);
    map.set(r.division,x);
  }
  return [...map.values()];
}

function renderPlanForecastV09(){
  const bridge=scopedPlan(data.fy_plan_bridge||[]);
  const perf=scopedPlan(data.budget_performance||[]);
  const budgets=scopedPlan(data.annual_budget||[]);
  const monthly=aggregateBudgetMonthly(perf);
  const divisions=aggregateBridgeByDivision(bridge);

  const fyBudgetRevenue=sumPlan(bridge,'fy_budget_revenue');
  const fyBudgetEbit=sumPlan(bridge,'fy_budget_ebit');
  const ytdBudgetRevenue=sumPlan(bridge,'ytd_budget_revenue');
  const ytdActualRevenue=sumPlan(bridge,'ytd_actual_revenue');
  const ytdBudgetEbit=sumPlan(bridge,'ytd_budget_ebit');
  const ytdActualEbit=sumPlan(bridge,'ytd_actual_ebit');
  const latestRevenue=sumPlan(bridge,'latest_fy_revenue');
  const latestEbit=sumPlan(bridge,'latest_fy_ebit');
  const fc1=sumPlan(bridge,'fc_1_fy_revenue');
  const fc3=sumPlan(bridge,'fc_3_fy_revenue');
  const fc6=sumPlan(bridge,'fc_6_fy_revenue');

  const currentBudgetRows=budgets.filter(r=>r.budget_year===data.meta.budget_year || Number(r.budget_year)===Number(data.meta.budget_year));
  const assumptions=[];
  const seen=new Set();
  for(const r of currentBudgetRows){
    const key=`${r.entity}|${r.division}`; if(seen.has(key))continue; seen.add(key);
    assumptions.push(r);
  }

  const forecast=data.forecast||[];
  const base=forecast.filter(r=>r.scenario==='Base'),up=forecast.filter(r=>r.scenario==='Upside'),down=forecast.filter(r=>r.scenario==='Downside');
  const sum12=rows=>rows.filter(r=>Number(r.horizon_month)<=12).reduce((s,r)=>s+(Number(r.revenue_forecast)||0),0);
  const acc=data.forecast_accuracy||[];

  return `<div class="kpi-grid">
    ${kpi('Budget vintage',safe(data.meta.budget_vintage||'-'),`FY ${safe(data.meta.budget_year||'')}`)}
    ${kpi('YTD revenue',eur.format(ytdActualRevenue),`${signed(ytdActualRevenue-ytdBudgetRevenue)} vs Budget`)}
    ${kpi('YTD EBIT',eur.format(ytdActualEbit),`${signed(ytdActualEbit-ytdBudgetEbit)} vs Budget`)}
    ${kpi('FY revenue outlook',eur.format(latestRevenue),`${pct(variancePct(latestRevenue,fyBudgetRevenue))} vs Budget`)}
    ${kpi('FY EBIT outlook',eur.format(latestEbit),`${signed(latestEbit-fyBudgetEbit)} vs Budget`)}
  </div>
  <div class="panel-grid">
    ${panel('YTD performance','Actual versus frozen Annual Budget',table(monthly,[
      {key:'month',label:'Month'},
      {key:'revenue',label:'Actual revenue',num:true,format:v=>eur.format(v)},
      {key:'revenue_budget',label:'Budget revenue',num:true,format:v=>eur.format(v)},
      {key:'revenue_variance',label:'Revenue variance',num:true,format:v=>signed(v)},
      {key:'ebit',label:'Actual EBIT',num:true,format:v=>eur.format(v)},
      {key:'ebit_budget',label:'Budget EBIT',num:true,format:v=>eur.format(v)},
      {key:'ebit_variance',label:'EBIT variance',num:true,format:v=>signed(v)}
    ]),'span-8')}
    ${panel('FY outlook evolution','How the expected full year moved as closes accumulated',metricRows([
      ['FY Budget',eur.format(fyBudgetRevenue)],
      ['FC-6 FY revenue',eur.format(fc6)],
      ['FC-3 FY revenue',eur.format(fc3)],
      ['FC-1 FY revenue',eur.format(fc1)],
      ['Latest FY revenue',eur.format(latestRevenue)],
      ['Latest vs Budget',signed(latestRevenue-fyBudgetRevenue)]
    ]),'span-4')}
    ${panel('Division plan bridge','YTD execution and latest full-year outlook',table(divisions,[
      {key:'division',label:'Division'},
      {key:'ytd_actual_revenue',label:'YTD Actual',num:true,format:v=>eur.format(v)},
      {key:'ytd_budget_revenue',label:'YTD Budget',num:true,format:v=>eur.format(v)},
      {key:'ytd_revenue_variance',label:'YTD Var.',num:true,format:v=>signed(v)},
      {key:'fy_budget_revenue',label:'FY Budget',num:true,format:v=>eur.format(v)},
      {key:'latest_fy_revenue',label:'Latest FY',num:true,format:v=>eur.format(v)},
      {key:'latest_fy_revenue_vs_budget',label:'FY Var.',num:true,format:v=>signed(v)},
      {key:'latest_fy_ebit',label:'Latest EBIT',num:true,format:v=>signed(v)}
    ]),'span-12')}
    ${panel('Budget monthly phasing','Frozen revenue plan',bars(aggregateBudgetMonthly(currentBudgetRows),'revenue_budget'),'span-7')}
    ${panel('Budget assumptions','Vintage-locked targets by entity and division',table(assumptions,[
      {key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'budget_model',label:'Model'},
      {key:'revenue_growth_target',label:'Growth',num:true,format:v=>pct(v)},
      {key:'gross_margin_target',label:'GM target',num:true,format:v=>Number(v)?pct(v):'-'},
      {key:'opex_pct_target',label:'OPEX %',num:true,format:v=>Number(v)?pct(v):'-'}
    ]),'span-5')}
    ${panel('Rolling forecast scenarios','Next 12 months remain dynamic; Budget remains frozen',metricRows([
      ['Base',eur.format(sum12(base))],['Upside',eur.format(sum12(up))],['Downside',eur.format(sum12(down))]
    ]),'span-4')}
    ${panel('Forecast accuracy','Historical realized vintages',table(acc,[
      {key:'horizon_month',label:'Horizon',format:v=>`${v}M`},
      {key:'mape',label:'MAPE',num:true,format:v=>pct(v)},
      {key:'bias',label:'Bias',num:true,format:v=>pct(v)},
      {key:'observations',label:'Observations',num:true}
    ]),'span-8')}
  </div>`;
}

renderers.forecast=renderPlanForecastV09;
const forecastViewV09=views.find(v=>v[0]==='forecast');
if(forecastViewV09){forecastViewV09[1]='Plan & Forecast';forecastViewV09[2]='Frozen Annual Budget, YTD performance, FY outlook and forecast vintages.';}
