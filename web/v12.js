const renderTreasuryBeforeForecast=renderers.treasury;
renderers.treasury=function(){
  const base=renderTreasuryBeforeForecast();
  const all=data.liquidity_forecast||[];
  const baseFc=all.filter(r=>r.scenario==='Base').sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month));
  const downFc=all.filter(r=>r.scenario==='Downside').sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month));
  const summaries=data.liquidity_forecast_summary||[];
  const allocation=data.capital_allocation_capacity||[];
  const b=summaries.find(r=>r.scenario==='Base')||{};
  const d=summaries.find(r=>r.scenario==='Downside')||{};
  const a=allocation.find(r=>r.scenario==='Downside')||allocation[0]||{};
  const extra=`<div class="section-note"><strong>12-month liquidity forecast:</strong> cash is projected from forecast revenue, AR, Inventory, AP, Contract Liabilities, tax, interest, CAPEX and debt amortization. RCF is drawn only when forecast cash would fall below the configured operating minimum.</div>
  <div class="kpi-grid">
    ${kpi('Base cash in 12M',eur.format(Number(b.ending_cash_12m)||0))}
    ${kpi('Base liquidity headroom',eur.format(Number(b.liquidity_headroom_12m)||0))}
    ${kpi('Downside minimum headroom',eur.format(Number(d.minimum_liquidity_headroom)||0))}
    ${kpi('Downside protected allocation capacity',eur.format(Number(a.downside_protected_allocation_capacity)||0),'After strategic liquidity buffer')}
    ${kpi('Base 12M covenant',safe(b.covenant_status_12m||'-'))}
    ${kpi('Downside 12M covenant',safe(d.covenant_status_12m||'-'))}
  </div>
  <div class="panel-grid">
    ${panel('Base liquidity outlook','12-month ending cash forecast',bars(baseFc,'ending_cash'),'span-7')}
    ${panel('Scenario liquidity summary','12-month position',table(summaries,[
      {key:'scenario',label:'Scenario'},
      {key:'ending_cash_12m',label:'Ending cash',num:true,format:v=>eur.format(v)},
      {key:'gross_debt_12m',label:'Gross debt',num:true,format:v=>eur.format(v)},
      {key:'liquidity_headroom_12m',label:'Headroom',num:true,format:v=>eur.format(v)},
      {key:'net_leverage_12m',label:'Net leverage',num:true,format:v=>`${num(v,2)}x`},
      {key:'covenant_status_12m',label:'Covenant'}
    ]),'span-5')}
    ${panel('Base liquidity bridge','Driver-based monthly forecast',table(baseFc,[
      {key:'month',label:'Month'},
      {key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},
      {key:'operating_cash_flow',label:'OCF',num:true,format:v=>signed(v)},
      {key:'capex',label:'CAPEX',num:true,format:v=>eur.format(v)},
      {key:'scheduled_debt_repayment',label:'Debt repayment',num:true,format:v=>eur.format(v)},
      {key:'rcf_draw',label:'RCF draw',num:true,format:v=>eur.format(v)},
      {key:'ending_cash',label:'Ending cash',num:true,format:v=>eur.format(v)},
      {key:'liquidity_headroom',label:'Headroom',num:true,format:v=>eur.format(v)}
    ]),'span-12')}
  </div>`;
  return base+extra;
};

const renderForecastBeforeLiquidity=renderers.forecast;
renderers.forecast=function(){
  const base=renderForecastBeforeLiquidity();
  const summaries=data.liquidity_forecast_summary||[];
  return base+`<div class="panel-grid">${panel('Liquidity by forecast scenario','Revenue scenarios flow through Working Capital, CAPEX, debt and RCF',table(summaries,[
    {key:'scenario',label:'Scenario'},
    {key:'forecast_operating_cash_flow_12m',label:'12M OCF',num:true,format:v=>signed(v)},
    {key:'forecast_capex_12m',label:'12M CAPEX',num:true,format:v=>eur.format(v)},
    {key:'ending_cash_12m',label:'12M cash',num:true,format:v=>eur.format(v)},
    {key:'maximum_rcf_drawn',label:'Max RCF',num:true,format:v=>eur.format(v)},
    {key:'minimum_liquidity_headroom',label:'Min headroom',num:true,format:v=>eur.format(v)}
  ]),'span-12')}</div>`;
};

const renderJourneyBeforeLiquidityForecast=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeLiquidityForecast()+`<div class="panel-grid">${panel('Forward liquidity model','Forecast operations become a projected cash and funding position',`<div class="section-note">The liquidity forecast advances the consolidated financial state once per month and scenario. Forecast revenue creates AR and customer cash, physical cost creates Inventory, operating accruals create AP, Software and Events create customer-funding liabilities, and the model then applies tax, interest, CAPEX, debt amortization and RCF capacity. Release controls enforce cash identities, complete scenario coverage and facility limits.</div>`,'span-12')}</div>`;
};
