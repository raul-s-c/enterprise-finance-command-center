const renderWCBeforeSupplierRisk=renderers['working-capital'];
renderers['working-capital']=function(){
  const base=renderWCBeforeSupplierRisk();
  const ap=latest(data.ap_aging_summary||[]);
  const supplierRows=scopedV04(data.ap_supplier_aging||[]).slice(0,40);
  const concentration=scopedV04(data.supplier_concentration||[]).slice(0,35);
  const totalAp=Number(ap.total_ap)||0;
  const overdue=Number(ap.overdue_ap)||0;
  const singleSource=Number(ap.single_source_ap)||0;
  const critical=Number(ap.critical_supplier_ap)||0;
  const extra=`<div class="section-note"><strong>Supplier payables:</strong> AP aging is reconstructed from legal supplier accruals and AP reductions and must reconcile exactly to account 2100_AP. Supplier identities are deterministic operating counterparts derived from those accruals rather than an unrelated supplier dataset.</div><div class="kpi-grid">${kpi('Gross trade payables',eur.format(totalAp),`${num(ap.supplier_count||0,0)} suppliers`)}${kpi('Overdue AP',eur.format(overdue),pct(ap.overdue_pct||0))}${kpi('AP >90 days',eur.format(ap.overdue_90_plus||0))}${kpi('Top-5 supplier concentration',pct(ap.top5_spend_concentration||0),'Trailing 12M spend')}${kpi('Single-source AP',eur.format(singleSource),totalAp?pct(singleSource/totalAp):'-')}${kpi('Critical supplier AP',eur.format(critical),totalAp?pct(critical/totalAp):'-')}</div><div class="panel-grid">${panel('AP aging','Gross supplier payables before cash settlement',metricRows([['Current',eur.format(ap.current||0)],['1-30 overdue',eur.format(ap.overdue_1_30||0)],['31-60 overdue',eur.format(ap.overdue_31_60||0)],['61-90 overdue',eur.format(ap.overdue_61_90||0)],['>90 overdue',eur.format(ap.overdue_90_plus||0)],['Weighted age',`${num(ap.weighted_age_days||0,1)} days`]]),'span-4')}${panel('Supplier concentration','Trailing-12-month external spend and current open exposure',table(concentration,[{key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'supplier_name',label:'Supplier'},{key:'supplier_category',label:'Category'},{key:'supplier_criticality',label:'Criticality',num:true},{key:'trailing_12m_spend',label:'12M spend',num:true,format:v=>eur.format(v)},{key:'supplier_spend_share',label:'Share',num:true,format:v=>pct(v)},{key:'total_ap',label:'Open AP',num:true,format:v=>eur.format(v)},{key:'risk_flag',label:'Risk'}]),'span-8')}${panel('Supplier aging watchlist','Open payables by derived supplier counterpart',table(supplierRows,[{key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'supplier_name',label:'Supplier'},{key:'supplier_category',label:'Category'},{key:'payment_terms_days',label:'Terms',num:true,format:v=>`${num(v,0)}d`},{key:'total_ap',label:'AP',num:true,format:v=>eur.format(v)},{key:'overdue_ap',label:'Overdue',num:true,format:v=>eur.format(v)},{key:'overdue_pct',label:'Overdue %',num:true,format:v=>pct(v)},{key:'single_source',label:'Single source',format:v=>v?'Yes':'No'}]),'span-12')}</div>`;
  return base+extra;
};

const renderJourneyBeforeSupplierRisk=renderers['data-journey'];
renderers['data-journey']=function(){
  return renderJourneyBeforeSupplierRisk()+`<div class="panel-grid">${panel('Three-way Working Capital integrity','AR + Inventory + AP schedules',`<div class="section-note">Customer AR aging reconciles to 1100_AR, SKU inventory aging reconciles to 1200_INVENTORY, and supplier AP aging reconciles to 2100_AP. Accounting allowances reduce AR and inventory carrying values without changing the gross operating schedules. The monthly release is blocked if any schedule diverges from its legal ledger balance.</div>`,'span-12')}</div>`;
};

const wcV08=views.find(v=>v[0]==='working-capital'); if(wcV08) wcV08[2]='AR, inventory and AP schedules, asset quality, supplier concentration and cash conversion.';
