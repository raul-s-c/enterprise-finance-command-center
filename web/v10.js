function scopedContracts(rows){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'entity'))) out=out.filter(r=>r.entity===state.entity);
  if(state.division!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'division'))) out=out.filter(r=>r.division===state.division);
  return out;
}

function contractCurrent(){
  const rows=scopedContracts(data.contract_entity_summary||[]);
  return rows.reduce((a,r)=>{
    a.liability+=Number(r.contract_liabilities)||0;
    a.advances+=Number(r.customer_advances)||0;
    return a;
  },{liability:0,advances:0});
}

const renderWCBeforeContracts=renderers['working-capital'];
renderers['working-capital']=function(){
  const base=renderWCBeforeContracts();
  const c=contractCurrent();
  const wc=latest(data.working_capital||[]);
  const detail=scopedContracts(data.contract_liability_detail||[]).slice(0,40);
  const tradeNwc=Number(wc.trade_net_working_capital)||Number(wc.net_working_capital)||0;
  const operatingNwc=Number(wc.operating_net_working_capital)||tradeNwc-c.liability;
  const extra=`<div class="section-note"><strong>Customer prepayments:</strong> Contract liabilities are operating funding, not revenue. Customer cash can arrive before service delivery; the liability is released only when the related Software service or Event project is recognized.</div>
  <div class="kpi-grid">
    ${kpi('Contract liabilities',eur.format(c.liability),'Customer cash received before service')}
    ${kpi('Current customer advances',eur.format(c.advances),'Cash received in latest close')}
    ${kpi('Trade NWC',eur.format(tradeNwc),'AR + Inventory - AP')}
    ${kpi('Operating NWC',eur.format(operatingNwc),'Including contract liabilities')}
  </div>
  <div class="panel-grid">
    ${panel('Contract-liability trend','Group closing customer prepayments',bars((data.contract_liability_summary||[]).slice(-24),'contract_liabilities'),'span-5')}
    ${panel('Open customer advances','Latest close; liability remains until service is delivered',table(detail,[
      {key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'customer',label:'Customer'},
      {key:'product_family',label:'Family'},{key:'quality_tier',label:'Tier'},
      {key:'receipt_month',label:'Receipt'},{key:'service_month',label:'Service'},
      {key:'contract_liability',label:'Liability',num:true,format:v=>eur.format(v)},
      {key:'months_to_service',label:'Months to service',num:true}
    ]),'span-7')}
  </div>`;
  return base+extra;
};

const renderBSBeforeContracts=renderers['balance-sheet'];
renderers['balance-sheet']=function(){
  const base=renderBSBeforeContracts();
  const rows=data.balance_sheet||[], l=latest(rows), c=contractCurrent();
  const extra=`<div class="panel-grid">${panel('Customer prepayment funding','Contract liabilities are included in total liabilities',metricRows([
    ['Contract liabilities',eur.format(Number(l.contract_liabilities)||c.liability)],
    ['Trade payables',eur.format(l.trade_payables||0)],
    ['Debt',eur.format(l.debt||0)],
    ['Customer funding / debt',Number(l.debt)?pct((Number(l.contract_liabilities)||c.liability)/Number(l.debt)):'-']
  ]),'span-5')}${panel('Contract liability trend','Cash precedes service recognition',bars((data.contract_liability_summary||[]).slice(-24),'contract_liabilities'),'span-7')}</div>`;
  return base+extra;
};

const renderDriversBeforeContracts=renderers['business-drivers'];
renderers['business-drivers']=function(){
  const base=renderDriversBeforeContracts();
  const c=contractCurrent();
  const rows=scopedContracts(data.contract_entity_summary||[]);
  const extra=`<div class="section-note"><strong>Prepayment economics</strong> — recurring Software contracts and Events deposits create operating funding before revenue recognition.</div>
  <div class="kpi-grid">${kpi('Open contract liabilities',eur.format(c.liability))}${kpi('Latest customer advances',eur.format(c.advances))}</div>
  <div class="panel-grid">${panel('Prepayment funding by business','Latest close',table(rows,[
    {key:'entity',label:'Entity'},{key:'division',label:'Division'},
    {key:'contract_liabilities',label:'Contract liabilities',num:true,format:v=>eur.format(v)},
    {key:'customer_advances',label:'Current advances',num:true,format:v=>eur.format(v)}
  ]),'span-6')}${panel('Group prepayment trend','Closing liability',bars((data.contract_liability_summary||[]).slice(-24),'contract_liabilities'),'span-6')}</div>`;
  return base+extra;
};

const renderJourneyBeforeContracts=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeContracts()+`<div class="panel-grid">${panel('Revenue recognition and customer advances','Cash and revenue are deliberately separated',`<div class="section-note">Software and Events may receive customer cash before the related service month. Advance cash posts to 2300_CONTRACT_LIABILITIES. When service is delivered, the liability is applied against the customer receivable while the original service transaction recognizes revenue. AR aging and ECL are rebuilt after this settlement layer, so prepayments reduce credit exposure without reducing recognized revenue.</div>`,'span-12')}</div>`;
};

const wcV10=views.find(v=>v[0]==='working-capital');if(wcV10)wcV10[2]='AR, inventory, AP and customer prepayments connected to cash conversion.';
