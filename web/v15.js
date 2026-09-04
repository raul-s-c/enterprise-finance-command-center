function fxScope(rows){
  let out=rows||[];
  if(state.entity!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'entity'))) out=out.filter(r=>r.entity===state.entity);
  if(state.division!=='all' && out.some(r=>Object.prototype.hasOwnProperty.call(r,'division'))) out=out.filter(r=>r.division===state.division);
  return out;
}

function renderFxTranslation(){
  const cc=fxScope(data.constant_currency||[]);
  const translation=fxScope(data.fx_translation||[]);
  const latestTranslation=translation.filter(r=>r.month===data.meta.end_month);
  const summary=data.fx_translation_summary||[];
  const revenueFx=cc.reduce((s,r)=>s+(Number(r.revenue_fx_effect)||0),0);
  const ebitFx=cc.reduce((s,r)=>s+(Number(r.ebit_fx_effect)||0),0);
  const cta=latestTranslation.reduce((s,r)=>s+(Number(r.fx_translation_reserve)||0),0);
  const foreign=latestTranslation.filter(r=>r.functional_currency!=='EUR');
  return `<div class="section-note"><strong>FX translation</strong> — functional-currency legal books are translated to EUR. Assets and liabilities use closing FX; share capital keeps its historical issue rate; retained earnings accumulate at the rates when profits arose; the residual translation difference is CTA/OCI.</div>
  <div class="kpi-grid">
    ${kpi('Translation reserve',eur.format(cta),'Entity scope · all divisions')}
    ${kpi('Revenue FX effect',signed(revenueFx),'Reported vs prior-year rates')}
    ${kpi('EBIT FX effect',signed(ebitFx),'Reported vs prior-year rates')}
    ${kpi('Group functional currencies',String(new Set((data.fx_translation||[]).map(r=>r.functional_currency)).size),'Group scope · not filtered')}
  </div>
  <div class="panel-grid">
    ${panel('Constant-currency performance','Current close translated at prior-year FX',table(cc,[
      {key:'entity',label:'Entity'},{key:'division',label:'Division'},{key:'functional_currency',label:'Currency'},
      {key:'reported_revenue',label:'Reported revenue',num:true,format:v=>eur.format(v)},
      {key:'constant_currency_revenue',label:'Constant currency',num:true,format:v=>eur.format(v)},
      {key:'revenue_fx_effect',label:'Revenue FX',num:true,format:v=>signed(v)},
      {key:'reported_ebit',label:'Reported EBIT',num:true,format:v=>eur.format(v)},
      {key:'ebit_fx_effect',label:'EBIT FX',num:true,format:v=>signed(v)}
    ]),'span-7')}
    ${panel('Closing FX & equity translation','Latest foreign entities',table(foreign,[
      {key:'entity',label:'Entity'},{key:'functional_currency',label:'Currency'},
      {key:'closing_fx_to_eur',label:'Closing FX',num:true,format:v=>num(v,5)},
      {key:'historical_equity_fx_to_eur',label:'Share capital FX',num:true,format:v=>num(v,5)},
      {key:'retained_earnings_effective_fx_to_eur',label:'RE effective FX',num:true,format:v=>num(v,5)},
      {key:'translated_share_capital',label:'Share capital',num:true,format:v=>eur.format(v)},
      {key:'translated_retained_earnings',label:'Retained earnings',num:true,format:v=>eur.format(v)},
      {key:'fx_translation_reserve',label:'CTA',num:true,format:v=>signed(v)}
    ]),'span-5')}
    ${panel('Translation reserve trend','Group CTA / OCI by close',bars(summary.slice(-24),'fx_translation_reserve'),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='fx')) views.splice(Math.max(views.length-1,0),0,['fx','FX & Translation','Functional-currency books, constant-currency performance and translation reserve.']);
renderers.fx=renderFxTranslation;

const journeyBeforeFx=renderers['data-journey'];
renderers['data-journey']=function(){
  return journeyBeforeFx()+`<div class="panel-grid">${panel('Multi-currency reporting','Functional currency → EUR translation',`<div class="section-note">Each legal journal has a functional-currency equivalent using monthly ECB FX when available. Local journals remain balanced after currency rounding. Assets and liabilities use closing FX, share capital uses historical FX and retained earnings accumulate at the monthly rates when profits arose. CTA/OCI isolates the remaining translation effect. Transaction-currency remeasurement is intentionally outside v0.15.</div>`,'span-12')}</div>`;
};
