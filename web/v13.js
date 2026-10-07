function statementScenario(name='Base'){
  return {
    pnl:(data.forecast_pnl||[]).filter(r=>r.scenario===name).sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month)),
    bs:(data.forecast_balance_sheet||[]).filter(r=>r.scenario===name).sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month)),
    cf:(data.forecast_cash_flow||[]).filter(r=>r.scenario===name).sort((a,b)=>Number(a.horizon_month)-Number(b.horizon_month))
  };
}

const renderPnlBeforeThreeStatement=renderers.pnl;
renderers.pnl=function(){
  const base=renderPnlBeforeThreeStatement();
  const f=statementScenario('Base').pnl;
  const total=f.filter(r=>Number(r.horizon_month)<=12).reduce((a,r)=>{for(const k of ['revenue','gross_profit','ebit','net_income'])a[k]+=Number(r[k])||0;return a},{revenue:0,gross_profit:0,ebit:0,net_income:0});
  const total24=f.reduce((a,r)=>{for(const k of ['revenue','gross_profit','ebit','net_income'])a[k]+=Number(r[k])||0;return a},{revenue:0,gross_profit:0,ebit:0,net_income:0});
  return base+`<div class="section-note"><strong>Forward P&L:</strong> the Base scenario links forecast Revenue, asset-quality reserve movements, depreciation, interest, tax and Net Income to the forecast Balance Sheet and Cash Flow. KPI cards distinguish the first 12 months from the full 24-month outlook.</div><div class="kpi-grid">${kpi('12M forecast revenue',eur.format(total.revenue))}${kpi('12M forecast EBIT',eur.format(total.ebit),pct(total.ebit/(total.revenue||1)))}${kpi('12M forecast net income',eur.format(total.net_income))}${kpi('24M forecast revenue',eur.format(total24.revenue))}${kpi('24M forecast EBIT',eur.format(total24.ebit),pct(total24.ebit/(total24.revenue||1)))}${kpi('24M forecast net income',eur.format(total24.net_income))}</div><div class="panel-grid">${panel('Base forecast P&L','Integrated 24-month statement · monthly source detail',table(f,[{key:'month',label:'Month'},{key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},{key:'gross_profit',label:'Gross profit',num:true,format:v=>eur.format(v)},{key:'depreciation',label:'Depreciation',num:true,format:v=>eur.format(v)},{key:'ebit',label:'EBIT',num:true,format:v=>signed(v)},{key:'interest',label:'Interest',num:true,format:v=>eur.format(v)},{key:'tax',label:'Tax',num:true,format:v=>eur.format(v)},{key:'net_income',label:'Net income',num:true,format:v=>signed(v)}]),'span-12')}</div>`;
};

const renderBSBeforeThreeStatement=renderers['balance-sheet'];
renderers['balance-sheet']=function(){
  const base=renderBSBeforeThreeStatement();
  const f=statementScenario('Base').bs;
  const l12=f.find(r=>Number(r.horizon_month)===12)||latest(f),l24=latest(f);
  return base+`<div class="section-note"><strong>Forward Balance Sheet:</strong> cash comes from the liquidity forecast; AR, Inventory, AP and Contract Liabilities come from operating drivers; PPE/CIP follows CAPEX; retained earnings follows forecast Net Income. No balancing plug is used. Balances are shown at each horizon-end, not summed.</div><div class="kpi-grid">${kpi('12M forecast assets',eur.format(Number(l12.assets)||0))}${kpi('12M forecast liabilities',eur.format(Number(l12.liabilities)||0))}${kpi('12M forecast equity',eur.format(Number(l12.equity)||0))}${kpi('12M balance check',eur.format(Number(l12.balance_check)||0))}${kpi('24M forecast assets',eur.format(Number(l24.assets)||0))}${kpi('24M forecast liabilities',eur.format(Number(l24.liabilities)||0))}${kpi('24M forecast equity',eur.format(Number(l24.equity)||0))}${kpi('24M balance check',eur.format(Number(l24.balance_check)||0))}</div><div class="panel-grid">${panel('Base forecast Balance Sheet','24-month linked financial position · month-end balances',table(f,[{key:'month',label:'Month'},{key:'cash',label:'Cash',num:true,format:v=>eur.format(v)},{key:'trade_receivables',label:'Net AR',num:true,format:v=>eur.format(v)},{key:'inventory',label:'Net inventory',num:true,format:v=>eur.format(v)},{key:'ppe_gross',label:'PPE',num:true,format:v=>eur.format(v)},{key:'cip',label:'CIP',num:true,format:v=>eur.format(v)},{key:'trade_payables',label:'AP',num:true,format:v=>eur.format(v)},{key:'contract_liabilities',label:'Contract liabilities',num:true,format:v=>eur.format(v)},{key:'debt',label:'Debt',num:true,format:v=>eur.format(v)},{key:'equity',label:'Equity',num:true,format:v=>eur.format(v)},{key:'balance_check',label:'Check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderCashBeforeThreeStatement=renderers['cash-flow'];
renderers['cash-flow']=function(){
  const base=renderCashBeforeThreeStatement();
  const f=statementScenario('Base').cf;
  const sumRows=rows=>rows.reduce((a,r)=>{for(const k of ['operating_cash_flow','investing_cash_flow','financing_cash_flow','free_cash_flow'])a[k]+=Number(r[k])||0;return a},{operating_cash_flow:0,investing_cash_flow:0,financing_cash_flow:0,free_cash_flow:0});
  const totals=sumRows(f.filter(r=>Number(r.horizon_month)<=12)),totals24=sumRows(f);
  return base+`<div class="kpi-grid">${kpi('12M forecast OCF',eur.format(totals.operating_cash_flow))}${kpi('12M forecast investing CF',eur.format(totals.investing_cash_flow))}${kpi('12M forecast financing CF',eur.format(totals.financing_cash_flow))}${kpi('12M forecast FCF',eur.format(totals.free_cash_flow))}${kpi('24M forecast OCF',eur.format(totals24.operating_cash_flow))}${kpi('24M forecast investing CF',eur.format(totals24.investing_cash_flow))}${kpi('24M forecast financing CF',eur.format(totals24.financing_cash_flow))}${kpi('24M forecast FCF',eur.format(totals24.free_cash_flow))}</div><div class="panel-grid">${panel('Base forecast Cash Flow','24-month monthly flows · linked to forecast Balance Sheet cash',table(f,[{key:'month',label:'Month'},{key:'operating_cash_flow',label:'Operating CF',num:true,format:v=>signed(v)},{key:'investing_cash_flow',label:'Investing CF',num:true,format:v=>signed(v)},{key:'financing_cash_flow',label:'Financing CF',num:true,format:v=>signed(v)},{key:'free_cash_flow',label:'Free cash flow',num:true,format:v=>signed(v)},{key:'ending_cash',label:'Ending cash',num:true,format:v=>eur.format(v)},{key:'cash_flow_identity_gap',label:'Check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderForecastBeforeThreeStatement=renderers.forecast;
renderers.forecast=function(){
  const base=renderForecastBeforeThreeStatement();
  const s=data.three_statement_forecast_summary||[];
  return base+`<div class="panel-grid">${panel('Integrated three-statement scenarios','12M flows and closing balances alongside the full 24M outlook',table(s,[{key:'scenario',label:'Scenario'},{key:'revenue_12m',label:'12M revenue',num:true,format:v=>eur.format(v)},{key:'ebit_12m',label:'12M EBIT',num:true,format:v=>signed(v)},{key:'free_cash_flow_12m',label:'12M FCF',num:true,format:v=>signed(v)},{key:'ending_cash_12m',label:'12M cash',num:true,format:v=>eur.format(v)},{key:'revenue_24m',label:'24M revenue',num:true,format:v=>eur.format(v)},{key:'ebit_24m',label:'24M EBIT',num:true,format:v=>signed(v)},{key:'free_cash_flow_24m',label:'24M FCF',num:true,format:v=>signed(v)},{key:'ending_cash_24m',label:'24M cash',num:true,format:v=>eur.format(v)},{key:'ending_balance_check_24m',label:'24M BS check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderJourneyBeforeThreeStatement=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeThreeStatement()+`<div class="panel-grid">${panel('Integrated three-statement forecast','One operating forecast, three linked financial statements',`<div class="section-note">Base, Upside and Downside forecasts now produce a linked P&L, Balance Sheet and Cash Flow. Working Capital and cash come from the liquidity model; CAPEX updates CIP/PPE and depreciation; reserve movements affect earnings and contra-assets; tax updates tax payable; Net Income updates retained earnings. The release fails if Assets do not equal Liabilities plus Equity or if forecast cash differs between Balance Sheet and Cash Flow.</div>`,'span-12')}</div>`;
};
