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
  return `<div class="section-note"><strong>FX translation</strong> — operating Revenue, local selling cost and Workforce cost originate from stable functional-currency economics before monthly EUR translation. The reporting ledger is then mirrored into functional-currency views for translation analytics. Assets and liabilities use closing FX; historical equity rates are preserved; the translation difference is CTA/OCI. Transaction-currency remeasurement is outside this release.</div>
  <div class="kpi-grid">
    ${kpi('Translation reserve',eur.format(cta),'CTA / OCI')}
    ${kpi('Revenue FX effect',signed(revenueFx),'Reported vs prior-year rates')}
    ${kpi('EBIT FX effect',signed(ebitFx),'Reported vs prior-year rates')}
    ${kpi('Functional currencies',String(new Set((data.fx_translation||[]).map(r=>r.functional_currency)).size))}
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

if(!views.some(v=>v[0]==='fx')) views.splice(Math.max(views.length-1,0),0,['fx','FX & Translation','Native operating FX, constant-currency performance and translation analytics.']);
renderers.fx=renderFxTranslation;

const journeyBeforeFx=renderers['data-journey'];
renderers['data-journey']=function(){
  return journeyBeforeFx()+`<div class="panel-grid">${panel('Multi-currency reporting','Functional currency → EUR reporting',`<div class="section-note">Commercial Revenue and local operating costs are anchored to stable functional-currency economics and translated monthly using ECB FX when available. Physical manufacturing cost follows the source-factory currency. The reporting ledger is also expressed in functional currency for local trial-balance and translation analysis. Assets/liabilities are translated at closing FX, historical equity rates are preserved and CTA/OCI isolates the translation effect. Foreign-currency monetary-item remeasurement and realized settlement FX are intentionally outside v0.15.</div>`,'span-12')}</div>`;
};
