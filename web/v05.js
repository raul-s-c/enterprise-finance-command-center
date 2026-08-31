function scopeV05(rows, entityField='entity'){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,entityField))) out=out.filter(r=>r[entityField]===state.entity);
  return out;
}

function lastMonthRows(rows){
  if(!rows?.length) return [];
  const month=[...rows].map(r=>r.month).sort().at(-1);
  return rows.filter(r=>r.month===month);
}

function aggregateSoftwareRows(rows){
  if(!rows?.length) return [];
  const map=new Map();
  for(const r of rows){
    const x=map.get(r.month)||{month:r.month,revenue:0,services_revenue:0,opening_mrr:0,ending_mrr:0,new_mrr:0,expansion_mrr:0,contraction_mrr:0,churn_mrr:0,arr:0,new_arr:0,expansion_arr:0,contraction_arr:0,churn_arr:0};
    for(const k of ['revenue','services_revenue','opening_mrr','ending_mrr','new_mrr','expansion_mrr','contraction_mrr','churn_mrr','arr','new_arr','expansion_arr','contraction_arr','churn_arr']) x[k]+=Number(r[k])||0;
    map.set(r.month,x);
  }
  return [...map.values()].sort((a,b)=>a.month.localeCompare(b.month)).map(x=>{
    x.recurring_revenue=x.ending_mrr;
    x.recurring_mix=x.revenue?x.recurring_revenue/x.revenue:0;
    x.nrr=x.opening_mrr?(x.opening_mrr+x.expansion_mrr-x.contraction_mrr-x.churn_mrr)/x.opening_mrr:0;
    x.grr=x.opening_mrr?(x.opening_mrr-x.contraction_mrr-x.churn_mrr)/x.opening_mrr:0;
    return x;
  });
}

function softwareBlock(){
  const raw=state.entity==='all'?(data.software_summary||[]):scopeV05(data.software_entity_summary||[]);
  const rows=state.entity==='all'?raw:aggregateSoftwareRows(raw);
  const l=latest(rows), detail=scopeV05(data.software_subscription_detail||[]).slice(0,25);
  return `<div class="kpi-grid">${kpi('ARR',eur.format(l.arr||0))}${kpi('NRR',pct(l.nrr||0),'Existing recurring base')}${kpi('GRR',pct(l.grr||0),'Before expansion')}${kpi('New ARR',eur.format(l.new_arr||0),'Current month')}${kpi('Churn ARR',eur.format(l.churn_arr||0),'Current month')}${kpi('Recurring mix',pct(l.recurring_mix||0))}</div><div class="panel-grid">${panel('ARR trend','Recurring revenue annualized',bars(rows.slice(-24),'arr'),'span-7')}${panel('ARR movement','Latest month',metricRows([['Opening ARR',eur.format((l.opening_mrr||0)*12)],['New ARR',eur.format(l.new_arr||0)],['Expansion ARR',eur.format(l.expansion_arr||0)],['Contraction ARR',eur.format(l.contraction_arr||0)],['Churn ARR',eur.format(l.churn_arr||0)],['Ending ARR',eur.format(l.arr||0)]]),'span-5')}${panel('Largest recurring positions','Latest customer-product recurring base',table(detail,[{key:'entity',label:'Entity'},{key:'customer',label:'Customer'},{key:'product_family',label:'Family'},{key:'product',label:'Product'},{key:'quality_tier',label:'Tier'},{key:'arr',label:'ARR',num:true,format:v=>eur.format(v)},{key:'new_arr',label:'New ARR',num:true,format:v=>eur.format(v)},{key:'churn_arr',label:'Churn ARR',num:true,format:v=>eur.format(v)}]),'span-12')}</div>`;
}

function eventsBlock(){
  const group=data.events_summary||[];
  const l=latest(group), detail=scopeV05(data.events_backlog_detail||[]).slice(0,30);
  const detailAgg=detail.reduce((a,r)=>{a.bookings+=(Number(r.bookings)||0);a.revenue+=(Number(r.recognized_revenue)||0);a.backlog+=(Number(r.ending_backlog)||0);return a},{bookings:0,revenue:0,backlog:0});
  const useSelected=state.entity!=='all' && detail.length;
  const bookings=useSelected?detailAgg.bookings:(l.bookings||0), revenue=useSelected?detailAgg.revenue:(l.recognized_revenue||0), backlog=useSelected?detailAgg.backlog:(l.ending_backlog||0);
  return `<div class="kpi-grid">${kpi('Bookings',eur.format(bookings))}${kpi('Recognized revenue',eur.format(revenue))}${kpi('Ending backlog',eur.format(backlog))}${kpi('Book-to-bill',num(revenue?bookings/revenue:0,2))}${kpi('Backlog coverage',`${num(l.backlog_coverage_months||0,1)} mo`)}</div><div class="panel-grid">${panel('Backlog trend','Group closing backlog',bars(group.slice(-24),'ending_backlog'),'span-7')}${panel('Bookings vs revenue','Latest group month',metricRows([['Opening backlog',eur.format(l.opening_backlog||0)],['Bookings',eur.format(l.bookings||0)],['Recognized revenue',eur.format(l.recognized_revenue||0)],['Ending backlog',eur.format(l.ending_backlog||0)],['Book-to-bill',num(l.book_to_bill||0,2)]]),'span-5')}${panel('Backlog by family','Latest close',table(detail,[{key:'entity',label:'Entity'},{key:'product_family',label:'Family'},{key:'bookings',label:'Bookings',num:true,format:v=>eur.format(v)},{key:'recognized_revenue',label:'Revenue',num:true,format:v=>eur.format(v)},{key:'ending_backlog',label:'Backlog',num:true,format:v=>eur.format(v)},{key:'book_to_bill',label:'Book-to-bill',num:true,format:v=>num(v,2)},{key:'backlog_coverage_months',label:'Coverage',num:true,format:v=>`${num(v,1)} mo`}]),'span-12')}</div>`;
}

function hardwareBlock(){
  let rows=data.hardware_factory_economics||[];
  if(state.entity!=='all' && ['CZ01','CN01'].includes(state.entity)) rows=rows.filter(r=>r.factory===state.entity);
  const current=lastMonthRows(rows), mix=data.hardware_mix||[];
  const totals=current.reduce((a,r)=>{a.produced+=Number(r.produced_units)||0;a.capacity+=Number(r.capacity_units)||0;a.under+=Number(r.under_absorption)||0;a.absorbed+=Number(r.absorbed_fixed_cost)||0;a.headroom+=Number(r.capacity_headroom_units)||0;return a},{produced:0,capacity:0,under:0,absorbed:0,headroom:0});
  const util=totals.capacity?totals.produced/totals.capacity:0;
  return `<div class="kpi-grid">${kpi('Factory utilization',pct(util))}${kpi('Production',num(totals.produced,0),'Units')}${kpi('Capacity headroom',num(totals.headroom,0),'Units')}${kpi('Absorbed fixed cost',eur.format(totals.absorbed))}${kpi('Under-absorption',eur.format(totals.under))}</div><div class="panel-grid">${panel('Factory economics','Latest month',table(current,[{key:'factory',label:'Factory'},{key:'factory_name',label:'Site'},{key:'produced_units',label:'Produced',num:true,format:v=>num(v,0)},{key:'capacity_units',label:'Capacity',num:true,format:v=>num(v,0)},{key:'utilization',label:'Utilization',num:true,format:v=>pct(v)},{key:'fixed_cost_per_produced_unit',label:'Fixed cost / unit',num:true,format:v=>eur.format(v)},{key:'under_absorption',label:'Under-absorption',num:true,format:v=>eur.format(v)}]),'span-7')}${panel('Production mix','Latest source-factory mix',table(mix,[{key:'source_factory',label:'Factory'},{key:'product_family',label:'Family'},{key:'quality_tier',label:'Tier'},{key:'units',label:'Units',num:true,format:v=>num(v,0)},{key:'unit_mix_pct',label:'Mix',num:true,format:v=>pct(v)},{key:'gross_margin_pct',label:'External GM',num:true,format:v=>pct(v)}]),'span-5')}</div>`;
}

function sparePartsBlock(){
  const rows=scopeV05(data.spare_parts_economics||[]), current=lastMonthRows(rows);
  const agg=current.reduce((a,r)=>{a.installed+=Number(r.ending_installed_base)||0;a.revenue+=Number(r.spare_parts_revenue)||0;a.units+=Number(r.spare_parts_units)||0;a.inventory+=Number(r.inventory_value)||0;a.usage+=(Number(r.inventory_value)||0)/(Number(r.inventory_coverage_months)||1);a.healthWeighted+=(Number(r.inventory_health_pct)||0)*(Number(r.inventory_value)||0);return a},{installed:0,revenue:0,units:0,inventory:0,usage:0,healthWeighted:0});
  const coverage=agg.usage?agg.inventory/agg.usage:0, health=agg.inventory?agg.healthWeighted/agg.inventory:1;
  return `<div class="kpi-grid">${kpi('Installed base',num(agg.installed,0),'Estimated active units')}${kpi('Aftermarket revenue',eur.format(agg.revenue))}${kpi('Revenue / installed unit',eur.format(agg.installed?agg.revenue/agg.installed:0))}${kpi('Inventory coverage',`${num(coverage,1)} mo`)}${kpi('Inventory health',pct(health))}</div><div class="panel-grid">${panel('Installed base by entity','Hardware additions feed future aftermarket opportunity',table(current,[{key:'entity',label:'Entity'},{key:'opening_installed_base',label:'Opening base',num:true,format:v=>num(v,0)},{key:'hardware_additions',label:'Additions',num:true,format:v=>num(v,0)},{key:'estimated_retirements',label:'Retirements',num:true,format:v=>num(v,0)},{key:'ending_installed_base',label:'Ending base',num:true,format:v=>num(v,0)},{key:'spare_parts_revenue',label:'Revenue',num:true,format:v=>eur.format(v)},{key:'revenue_per_installed_unit',label:'Revenue / installed',num:true,format:v=>eur.format(v)}]),'span-7')}${panel('Aftermarket trend','Trailing 24 months',bars(rows.slice(-24),'spare_parts_revenue'),'span-5')}</div>`;
}

function renderBusinessDrivers(){
  const blocks=[];
  const show=d=>state.division==='all'||state.division===d;
  if(show('Software')) blocks.push(`<div class="section-note"><strong>Software</strong> — recurring revenue, retention and ARR movement.</div>${softwareBlock()}`);
  if(show('Events')) blocks.push(`<div class="section-note"><strong>Events & Projects</strong> — bookings, backlog and conversion to recognized revenue.</div>${eventsBlock()}`);
  if(show('Hardware')) blocks.push(`<div class="section-note"><strong>Hardware</strong> — factory capacity, fixed-cost absorption and production mix.</div>${hardwareBlock()}`);
  if(show('Spare Parts')) blocks.push(`<div class="section-note"><strong>Spare Parts</strong> — installed base, aftermarket monetization and inventory coverage.</div>${sparePartsBlock()}`);
  return blocks.join('')||'<div class="empty">No divisional driver schedule is available for this selection.</div>';
}

if(!views.some(v=>v[0]==='business-drivers')) views.splice(1,0,['business-drivers','Business Drivers','Division-specific operating economics behind the financial statements.']);
renderers['business-drivers']=renderBusinessDrivers;
