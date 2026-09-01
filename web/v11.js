function scopedTreasury(rows){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'entity'))) out=out.filter(r=>r.entity===state.entity);
  return out;
}

function renderTreasury(){
  const liq=data.treasury_liquidity||[];
  const l=latest(liq);
  const entities=scopedTreasury(data.treasury_entity_cash||[]);
  const pool=data.treasury_cash_pool||[];
  const debt=scopedTreasury(data.debt_schedule||[]);
  const maturity=data.debt_maturity_ladder||[];
  const groupCash=Number(l.cash)||entities.reduce((s,r)=>s+(Number(r.cash)||0),0);
  const grossDebt=Number(l.gross_debt)||debt.reduce((s,r)=>s+(Number(r.gross_debt)||0),0);
  const netDebt=Number(l.net_debt)||grossDebt-groupCash;
  const poolTotal=pool.reduce((s,r)=>s+(Number(r.amount)||0),0);
  return `<div class="kpi-grid">
    ${kpi('Group cash',eur.format(groupCash),'Post cash-pooling')}
    ${kpi('Gross debt',eur.format(grossDebt))}
    ${kpi(netDebt>=0?'Net debt':'Net cash',eur.format(Math.abs(netDebt)))}
    ${kpi('Liquidity headroom',eur.format(Number(l.liquidity_headroom)||0),'Cash above minimum + undrawn RCF')}
    ${kpi('Net leverage',num(Number(l.net_leverage)||0,2),`Limit ${num(Number(l.net_leverage_limit)||0,2)}x`)}
    ${kpi('Interest coverage',`${num(Number(l.interest_coverage)||0,1)}x`,`Minimum ${num(Number(l.interest_coverage_min)||0,1)}x`)}
    ${kpi('Covenant status',safe(l.covenant_status||'-'))}
  </div>
  <div class="panel-grid">
    ${panel('Liquidity trend','Cash, leverage and covenant headroom',table(liq.slice(-24),[
      {key:'month',label:'Month'},
      {key:'cash',label:'Cash',num:true,format:v=>eur.format(v)},
      {key:'gross_debt',label:'Gross debt',num:true,format:v=>eur.format(v)},
      {key:'net_debt',label:'Net debt',num:true,format:v=>signed(v)},
      {key:'liquidity_headroom',label:'Liquidity headroom',num:true,format:v=>eur.format(v)},
      {key:'net_leverage',label:'Net leverage',num:true,format:v=>`${num(v,2)}x`},
      {key:'interest_coverage',label:'Interest cover',num:true,format:v=>`${num(v,1)}x`},
      {key:'covenant_status',label:'Covenant'}
    ]),'span-8')}
    ${panel('Current liquidity bridge','Latest group position',metricRows([
      ['Group cash',eur.format(groupCash)],
      ['Minimum operating cash',eur.format(Number(l.minimum_operating_cash)||0)],
      ['Undrawn RCF',eur.format(Number(l.undrawn_rcf)||0)],
      ['Liquidity headroom',eur.format(Number(l.liquidity_headroom)||0)],
      ['Latest cash-pool transfers',eur.format(poolTotal)]
    ]),'span-4')}
    ${panel('Cash by legal entity','Post-pooling legal cash and funding position',table(entities,[
      {key:'entity',label:'Entity'},
      {key:'cash',label:'Cash',num:true,format:v=>eur.format(v)},
      {key:'minimum_cash',label:'Minimum cash',num:true,format:v=>eur.format(v)},
      {key:'cash_above_minimum',label:'Above / (below) minimum',num:true,format:v=>signed(v)},
      {key:'gross_debt',label:'Debt',num:true,format:v=>eur.format(v)},
      {key:'net_debt',label:'Net debt',num:true,format:v=>signed(v)},
      {key:'implied_annual_interest_rate',label:'Implied rate',num:true,format:v=>pct(v)},
      {key:'contractual_maturity',label:'Maturity'}
    ]),'span-8')}
    ${panel('Debt maturity ladder','Contractual debt outstanding at latest close',table(maturity,[
      {key:'contractual_maturity',label:'Maturity'},
      {key:'maturity_year',label:'Year',num:true},
      {key:'maturing_debt',label:'Maturing debt',num:true,format:v=>eur.format(v)}
    ]),'span-4')}
    ${panel('Latest cash-pool movements','Internal liquidity concentration; group cash impact is zero',table(pool,[
      {key:'source_entity',label:'Source'},
      {key:'destination_entity',label:'Destination'},
      {key:'transfer_type',label:'Type'},
      {key:'amount',label:'Amount',num:true,format:v=>eur.format(v)}
    ]),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='treasury')){
  const cashIdx=views.findIndex(v=>v[0]==='cash-flow');
  views.splice(cashIdx>=0?cashIdx+1:5,0,['treasury','Treasury','Cash concentration, debt, liquidity headroom and covenant monitoring.']);
}
renderers.treasury=renderTreasury;

const renderCashBeforeTreasury=renderers['cash-flow'];
renderers['cash-flow']=function(){
  const base=renderCashBeforeTreasury();
  const liq=latest(data.treasury_liquidity||[]);
  return base+`<div class="panel-grid">${panel('Treasury overlay','Cash pooling reallocates liquidity between legal entities without changing consolidated cash',metricRows([
    ['Group cash',eur.format(Number(liq.cash)||0)],
    ['Gross debt',eur.format(Number(liq.gross_debt)||0)],
    ['Liquidity headroom',eur.format(Number(liq.liquidity_headroom)||0)],
    ['Covenant status',safe(liq.covenant_status||'-')]
  ]),'span-12')}</div>`;
};

const renderJourneyBeforeTreasury=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeTreasury()+`<div class="panel-grid">${panel('Treasury and liquidity','Legal cash concentration with consolidated elimination',`<div class="section-note">Cash pooling creates reciprocal intercompany treasury receivables and payables. Subsidiaries retain configured operating minimums while surplus cash is concentrated at HQ or local shortfalls are funded. Pooling must leave consolidated cash unchanged, treasury receivables must equal treasury payables, and debt schedules must reconcile to account 2500_DEBT.</div>`,'span-12')}</div>`;
};
