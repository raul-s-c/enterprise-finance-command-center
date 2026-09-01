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
  return `<div class="section-note"><strong>FX translation</strong> — legal activity is maintained in functional currency and translated to EUR. Assets and liabilities use closing FX; share capital uses historical FX; translation differences are reported as CTA/OCI.</div>
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
    ]),'span-8')}
    ${panel('Closing FX & CTA','Latest foreign entities',table(foreign,[
      {key:'entity',label:'Entity'},{key:'functional_currency',label:'Currency'},
      {key:'closing_fx_to_eur',label:'Closing FX',num:true,format:v=>num(v,5)},
      {key:'historical_equity_fx_to_eur',label:'Historical equity FX',num:true,format:v=>num(v,5)},
      {key:'fx_translation_reserve',label:'CTA',num:true,format:v=>signed(v)}
    ]),'span-4')}
    ${panel('Translation reserve trend','Group CTA / OCI by close',bars(summary.slice(-24),'fx_translation_reserve'),'span-12')}
  </div>`;
}

if(!views.some(v=>v[0]==='fx')) views.splice(Math.max(views.length-1,0),0,['fx','FX & Translation','Functional-currency books, constant-currency performance and translation reserve.']);
renderers.fx=renderFxTranslation;

const journeyBeforeFx=renderers['data-journey'];
renderers['data-journey']=function(){
  return journeyBeforeFx()+`<div class="panel-grid">${panel('Multi-currency reporting','Functional currency → EUR translation',`<div class="section-note">Each legal journal has a functional-currency equivalent using monthly ECB FX when available. Local trial balances are translated to EUR using closing FX for assets/liabilities and historical FX for share capital. The resulting foreign currency translation difference is isolated in CTA/OCI. Reported revenue and EBIT are also shown at prior-year FX for constant-currency analysis.</div>`,'span-12')}</div>`;
};
