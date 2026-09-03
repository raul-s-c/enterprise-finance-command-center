function transactionFxScope(rows){
  let out=rows||[];
  if(state.entity!=='all') out=out.filter(r=>r.entity===state.entity);
  if(state.division!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'division'))) out=out.filter(r=>r.division===state.division);
  return out;
}

function transactionFxCurrent(){
  return transactionFxScope(data.transaction_fx_close_documents||[]);
}

function transactionFxCurrencySummary(){
  const rows=transactionFxCurrent().filter(r=>r.status==='Open'),map=new Map();
  for(const r of rows){
    const key=r.transaction_currency,x=map.get(key)||{transaction_currency:key,open_documents:0,gross_receivable_eur:0,gross_payable_eur:0,net_exposure_eur:0};
    x.open_documents+=1;
    if(r.document_type==='Receivable') x.gross_receivable_eur+=Number(r.carrying_reporting_eur)||0;
    else x.gross_payable_eur+=Number(r.carrying_reporting_eur)||0;
    x.net_exposure_eur=x.gross_receivable_eur-x.gross_payable_eur;
    map.set(key,x);
  }
  return [...map.values()].sort((a,b)=>Math.abs(b.net_exposure_eur)-Math.abs(a.net_exposure_eur));
}

function renderTransactionFx(){
  const rows=transactionFxCurrent(),open=rows.filter(r=>r.status==='Open'),currency=transactionFxCurrencySummary();
  const unrealized=rows.reduce((s,r)=>s+(Number(r.unrealized_fx_gain_loss_eur)||0),0);
  const realized=rows.reduce((s,r)=>s+(Number(r.realized_fx_gain_loss_eur)||0),0);
  const net=currency.reduce((s,r)=>s+r.net_exposure_eur,0);
  return `<div class="section-note"><strong>Transaction FX subledger</strong> — invoice-currency receivables and payables are remeasured in each entity's functional currency. Realized and unrealized FX remain separate from CTA and every document retains its source journal.</div>
  <div class="kpi-grid">
    ${kpi('Open FX documents',String(open.length),'Current close')}
    ${kpi('Net transaction exposure',signed(net),'Receivables less payables')}
    ${kpi('Unrealized FX P&L',signed(unrealized),'Current remeasurement')}
    ${kpi('Realized FX P&L',signed(realized),'Settlements in close')}
  </div>
  <div class="panel-grid">
    ${panel('Exposure by transaction currency','Open documents at current closing FX',table(currency,[
      {key:'transaction_currency',label:'Currency'},{key:'open_documents',label:'Documents',num:true},
      {key:'gross_receivable_eur',label:'Receivables',num:true,format:v=>eur.format(v)},
      {key:'gross_payable_eur',label:'Payables',num:true,format:v=>eur.format(v)},
      {key:'net_exposure_eur',label:'Net exposure',num:true,format:v=>signed(v)}
    ]),'span-5')}
    ${panel('Largest open transaction exposures','Source-tied documents in selected scope',table(open.slice(0,20),[
      {key:'document_id',label:'Document'},{key:'entity',label:'Entity'},{key:'division',label:'Division'},
      {key:'document_type',label:'Type'},{key:'transaction_currency',label:'Currency'},
      {key:'age_months',label:'Age',num:true},{key:'carrying_reporting_eur',label:'EUR carrying',num:true,format:v=>eur.format(v)},
      {key:'cumulative_fx_gain_loss_eur',label:'Cumulative FX',num:true,format:v=>signed(v)}
    ]),'span-7')}
  </div>`;
}

const renderFxBeforeTransaction=renderers.fx;
renderers.fx=function(){return renderFxBeforeTransaction()+renderTransactionFx();};

const journeyBeforeTransactionFx=renderers['data-journey'];
renderers['data-journey']=function(){
  return journeyBeforeTransactionFx()+`<div class="panel-grid">${panel('Transaction FX lifecycle','Source journal → contract currency → functional remeasurement → settlement',`<div class="section-note">Foreign-currency AR and AP documents preserve issue and settlement month, functional and transaction currency, original amounts, closing carrying value and monthly realized/unrealized P&L. Document, rate, lifecycle and summary identities block the release on any unexplained difference.</div>`,'span-12')}</div>`;
};
