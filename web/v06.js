function hardwareBlock(){
  let rows=data.hardware_factory_economics||[];
  if(state.entity!=='all' && ['CZ01','CN01'].includes(state.entity)) rows=rows.filter(r=>r.factory===state.entity);
  const current=lastMonthRows(rows), mix=data.hardware_mix||[];
  const totals=current.reduce((a,r)=>{
    a.produced+=Number(r.produced_units)||0;
    a.capacity+=Number(r.capacity_units)||0;
    a.actual+=Number(r.actual_fixed_factory_cost)||Number(r.fixed_factory_cost)||0;
    a.absorbed+=Number(r.absorbed_fixed_cost)||0;
    a.variance+=Number(r.absorption_variance)||0;
    a.under+=Number(r.under_absorption)||0;
    a.over+=Number(r.over_absorption)||0;
    a.headroom+=Number(r.capacity_headroom_units)||0;
    return a;
  },{produced:0,capacity:0,actual:0,absorbed:0,variance:0,under:0,over:0,headroom:0});
  const util=totals.capacity?totals.produced/totals.capacity:0;
  const absorption=totals.actual?totals.absorbed/totals.actual:0;
  return `<div class="kpi-grid">${kpi('Factory utilization',pct(util))}${kpi('Production',num(totals.produced,0),'Units')}${kpi('Capacity headroom',num(totals.headroom,0),'Units')}${kpi('Actual fixed factory cost',eur.format(totals.actual))}${kpi('Absorbed fixed cost',eur.format(totals.absorbed),pct(absorption))}${kpi('Absorption variance',eur.format(totals.variance),totals.variance>=0?'Under-absorption':'Over-absorption')}</div><div class="panel-grid">${panel('Factory absorption accounting','Latest month; variance is posted to Gross Profit',table(current,[{key:'factory',label:'Factory'},{key:'factory_name',label:'Site'},{key:'produced_units',label:'Produced',num:true,format:v=>num(v,0)},{key:'capacity_units',label:'Capacity',num:true,format:v=>num(v,0)},{key:'utilization',label:'Utilization',num:true,format:v=>pct(v)},{key:'actual_fixed_factory_cost',label:'Actual fixed cost',num:true,format:v=>eur.format(v)},{key:'absorbed_fixed_cost',label:'Absorbed',num:true,format:v=>eur.format(v)},{key:'absorption_variance',label:'Variance',num:true,format:v=>signed(v)},{key:'fixed_cost_absorption_pct',label:'Absorption',num:true,format:v=>pct(v)}]),'span-7')}${panel('Production mix','Latest source-factory mix',table(mix,[{key:'source_factory',label:'Factory'},{key:'product_family',label:'Family'},{key:'quality_tier',label:'Tier'},{key:'units',label:'Units',num:true,format:v=>num(v,0)},{key:'unit_mix_pct',label:'Mix',num:true,format:v=>pct(v)},{key:'gross_margin_pct',label:'External GM',num:true,format:v=>pct(v)}]),'span-5')}</div>`;
}

const renderPnlBeforeFactoryAbsorption=renderers.pnl;
renderers.pnl=function(){
  const current=(data.management_detail||[]).filter(r=>r.month===data.meta.end_month);
  const variance=current.reduce((s,r)=>s+(Number(r.factory_absorption_variance)||0),0);
  const note=`<div class="section-note"><strong>Factory absorption:</strong> ${eur.format(variance)} is included in current-month Gross Profit. Positive values are under-absorption costs; negative values are over-absorption benefits.</div>`;
  return note+renderPnlBeforeFactoryAbsorption();
};
