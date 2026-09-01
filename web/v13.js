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
  const total=f.reduce((a,r)=>{for(const k of ['revenue','gross_profit','ebit','net_income'])a[k]+=Number(r[k])||0;return a},{revenue:0,gross_profit:0,ebit:0,net_income:0});
  return base+`<div class="section-note"><strong>Forward P&L:</strong> the Base scenario now links forecast Revenue, asset-quality reserve movements, depreciation, interest, tax and Net Income to the forecast Balance Sheet and Cash Flow.</div><div class="kpi-grid">${kpi('12M forecast revenue',eur.format(total.revenue))}${kpi('12M forecast EBIT',eur.format(total.ebit),pct(total.ebit/(total.revenue||1)))}${kpi('12M forecast net income',eur.format(total.net_income))}</div><div class="panel-grid">${panel('Base forecast P&L','Integrated 12-month statement',table(f,[{key:'month',label:'Month'},{key:'revenue',label:'Revenue',num:true,format:v=>eur.format(v)},{key:'gross_profit',label:'Gross profit',num:true,format:v=>eur.format(v)},{key:'depreciation',label:'Depreciation',num:true,format:v=>eur.format(v)},{key:'ebit',label:'EBIT',num:true,format:v=>signed(v)},{key:'interest',label:'Interest',num:true,format:v=>eur.format(v)},{key:'tax',label:'Tax',num:true,format:v=>eur.format(v)},{key:'net_income',label:'Net income',num:true,format:v=>signed(v)}]),'span-12')}</div>`;
};

const renderBSBeforeThreeStatement=renderers['balance-sheet'];
renderers['balance-sheet']=function(){
  const base=renderBSBeforeThreeStatement();
  const f=statementScenario('Base').bs;
  const l=latest(f);
  return base+`<div class="section-note"><strong>Forward Balance Sheet:</strong> cash comes from the liquidity forecast; AR, Inventory, AP and Contract Liabilities come from operating drivers; PPE/CIP follows CAPEX; retained earnings follows forecast Net Income. No balancing plug is used.</div><div class="kpi-grid">${kpi('12M forecast assets',eur.format(Number(l.assets)||0))}${kpi('12M forecast liabilities',eur.format(Number(l.liabilities)||0))}${kpi('12M forecast equity',eur.format(Number(l.equity)||0))}${kpi('12M balance check',eur.format(Number(l.balance_check)||0))}</div><div class="panel-grid">${panel('Base forecast Balance Sheet','12-month linked financial position',table(f,[{key:'month',label:'Month'},{key:'cash',label:'Cash',num:true,format:v=>eur.format(v)},{key:'trade_receivables',label:'Net AR',num:true,format:v=>eur.format(v)},{key:'inventory',label:'Net inventory',num:true,format:v=>eur.format(v)},{key:'ppe_gross',label:'PPE',num:true,format:v=>eur.format(v)},{key:'cip',label:'CIP',num:true,format:v=>eur.format(v)},{key:'trade_payables',label:'AP',num:true,format:v=>eur.format(v)},{key:'contract_liabilities',label:'Contract liabilities',num:true,format:v=>eur.format(v)},{key:'debt',label:'Debt',num:true,format:v=>eur.format(v)},{key:'equity',label:'Equity',num:true,format:v=>eur.format(v)},{key:'balance_check',label:'Check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderCashBeforeThreeStatement=renderers['cash-flow'];
renderers['cash-flow']=function(){
  const base=renderCashBeforeThreeStatement();
  const f=statementScenario('Base').cf;
  const totals=f.reduce((a,r)=>{for(const k of ['operating_cash_flow','investing_cash_flow','financing_cash_flow','free_cash_flow'])a[k]+=Number(r[k])||0;return a},{operating_cash_flow:0,investing_cash_flow:0,financing_cash_flow:0,free_cash_flow:0});
  return base+`<div class="kpi-grid">${kpi('12M forecast OCF',eur.format(totals.operating_cash_flow))}${kpi('12M forecast investing CF',eur.format(totals.investing_cash_flow))}${kpi('12M forecast financing CF',eur.format(totals.financing_cash_flow))}${kpi('12M forecast FCF',eur.format(totals.free_cash_flow))}</div><div class="panel-grid">${panel('Base forecast Cash Flow','Linked to forecast Balance Sheet cash',table(f,[{key:'month',label:'Month'},{key:'operating_cash_flow',label:'Operating CF',num:true,format:v=>signed(v)},{key:'investing_cash_flow',label:'Investing CF',num:true,format:v=>signed(v)},{key:'financing_cash_flow',label:'Financing CF',num:true,format:v=>signed(v)},{key:'free_cash_flow',label:'Free cash flow',num:true,format:v=>signed(v)},{key:'ending_cash',label:'Ending cash',num:true,format:v=>eur.format(v)},{key:'cash_flow_identity_gap',label:'Check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderForecastBeforeThreeStatement=renderers.forecast;
renderers.forecast=function(){
  const base=renderForecastBeforeThreeStatement();
  const s=data.three_statement_forecast_summary||[];
  return base+`<div class="panel-grid">${panel('Integrated three-statement scenarios','12-month P&L, Balance Sheet and Cash Flow consequences',table(s,[{key:'scenario',label:'Scenario'},{key:'revenue_12m',label:'Revenue',num:true,format:v=>eur.format(v)},{key:'ebit_12m',label:'EBIT',num:true,format:v=>signed(v)},{key:'net_income_12m',label:'Net income',num:true,format:v=>signed(v)},{key:'free_cash_flow_12m',label:'FCF',num:true,format:v=>signed(v)},{key:'ending_cash_12m',label:'Ending cash',num:true,format:v=>eur.format(v)},{key:'ending_assets_12m',label:'Assets',num:true,format:v=>eur.format(v)},{key:'ending_equity_12m',label:'Equity',num:true,format:v=>eur.format(v)},{key:'ending_balance_check',label:'BS check',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
};

const renderJourneyBeforeThreeStatement=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeThreeStatement()+`<div class="panel-grid">${panel('Integrated three-statement forecast','One operating forecast, three linked financial statements',`<div class="section-note">Base, Upside and Downside forecasts now produce a linked P&L, Balance Sheet and Cash Flow. Working Capital and cash come from the liquidity model; CAPEX updates CIP/PPE and depreciation; reserve movements affect earnings and contra-assets; tax updates tax payable; Net Income updates retained earnings. The release fails if Assets do not equal Liabilities plus Equity or if forecast cash differs between Balance Sheet and Cash Flow.</div>`,'span-12')}</div>`;
};
