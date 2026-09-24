/* Published three-statement scenario and group workforce outlook, never a second forecast engine. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const number=value=>Number.isFinite(Number(value))?Number(value):0;
  const money=value=>`€${(number(value)/1e6).toFixed(1)}m`;
  const fte=value=>number(value).toFixed(0);
  const metrics=[['revenue_12m','Revenue'],['ebit_12m','EBIT'],['free_cash_flow_12m','Free cash flow'],['ending_cash_12m','Ending cash']];
  let selectedMetric='ebit_12m';

  function scenarios(rows,metric=selectedMetric){
    const ordered=['Downside','Base','Upside'].map(name=>(rows||[]).find(row=>row.scenario===name)).filter(Boolean);
    if(!ordered.length)return '<p class="fs-empty">No published scenario summary.</p>';
    const key=metrics.some(([item])=>item===metric)?metric:'ebit_12m',base=ordered.find(row=>row.scenario==='Base')||{},maximum=Math.max(...ordered.map(row=>Math.abs(number(row[key]))),1);
    const bars=ordered.map(row=>{
      const value=number(row[key]),difference=value-number(base[key]),tone=row.scenario==='Base'?'base':row.scenario==='Upside'?'upside':'downside';
      return `<div class="fs-scenario ${tone}"><strong>${escape(row.scenario)}</strong><div class="fs-scenario-track"><i style="width:${(Math.abs(value)/maximum*100).toFixed(2)}%"></i></div><b>${money(value)}</b><small>${row.scenario==='Base'?'Reference':`${difference>=0?'+':'−'}${money(Math.abs(difference))} vs Base`}</small></div>`;
    }).join('');
    const balance=number(base.ending_assets_12m)-number(base.ending_liabilities_12m)-number(base.ending_equity_12m);
    return `<div class="fs-visual" aria-label="Published three-statement scenario comparison">
      <div class="fs-metric-switch" role="group" aria-label="Compare forecast metric">${metrics.map(([item,label])=>`<button type="button" data-fs-metric="${item}" aria-pressed="${item===key}">${label}</button>`).join('')}</div>
      <div class="fs-scenarios">${bars}</div>
      <div class="fs-statement-link"><div><span>Base P&amp;L</span><strong>${money(base.revenue_12m)} revenue → ${money(base.ebit_12m)} EBIT</strong></div><div><span>Base cash flow</span><strong>${money(base.free_cash_flow_12m)} FCF → ${money(base.ending_cash_12m)} cash</strong></div></div>
      <div class="fs-balance"><span>Base balance sheet</span><strong>${money(base.ending_assets_12m)} assets = ${money(base.ending_liabilities_12m)} liabilities + ${money(base.ending_equity_12m)} equity</strong><small class="${Math.abs(balance)<.01?'fs-pass':'fs-fail'}">Balance check ${money(Math.abs(balance))}${Math.abs(balance)<.01?' · reconciled':' · review'}</small></div>
    </div>`;
  }

  function workforceMonths(rows,endMonth){
    const selected=(rows||[]).filter(row=>row.scenario==='Base'&&row.vintage===endMonth&&number(row.horizon_month)<=12);
    const byMonth=new Map();
    for(const row of selected){
      const value=byMonth.get(row.month)||{month:row.month,fte:0,target:0,hires:0,personnel:0,nonPeople:0,opex:0};
      value.fte+=number(row.workforce_fte_forecast);value.target+=number(row.workforce_target_fte);
      value.hires+=number(row.workforce_hires_forecast);value.personnel+=number(row.personnel_cost_forecast);
      value.nonPeople+=number(row.non_people_opex_forecast);value.opex+=number(row.opex_forecast);
      byMonth.set(row.month,value);
    }
    return [...byMonth.values()].sort((a,b)=>a.month.localeCompare(b.month));
  }
  function workforce(rows){
    if(!rows.length)return '<p class="fs-empty">No published Base workforce outlook.</p>';
    const last=rows.at(-1),hires=rows.reduce((sum,row)=>sum+row.hires,0);
    const personnel=rows.reduce((sum,row)=>sum+row.personnel,0),nonPeople=rows.reduce((sum,row)=>sum+row.nonPeople,0);
    const maximum=Math.max(...rows.flatMap(row=>[row.fte,row.target]),1),minimum=Math.min(...rows.flatMap(row=>[row.fte,row.target]));
    const y=value=>70-(value-minimum)/(maximum-minimum||1)*52;
    const path=key=>rows.map((row,index)=>`${index?'L':'M'}${(8+index*284/Math.max(rows.length-1,1)).toFixed(1)},${y(row[key]).toFixed(1)}`).join(' ');
    return `<div class="fs-visual" aria-label="Published group Base workforce outlook">
      <div class="fs-workforce-head"><div><span>Ending FTE · ${escape(last.month)}</span><strong>${fte(last.fte)}</strong><small>Forecast headcount</small></div><div><span>Target FTE</span><strong>${fte(last.target)}</strong><small>Operating target, not actual</small></div><div><span>12M planned hires</span><strong>${fte(hires)}</strong><small>Across all entities</small></div></div>
      <div class="fs-trend-head"><strong>Forecast FTE vs target</strong><span>12 months · people</span></div>
      <svg class="fs-fte-chart" viewBox="0 0 300 94" preserveAspectRatio="none" role="img" aria-label="${escape(rows.map(row=>`${row.month}: forecast ${fte(row.fte)} FTE, target ${fte(row.target)} FTE`).join('; '))}"><line x1="8" x2="292" y1="78" y2="78"/><path class="fs-forecast" d="${path('fte')}"/><path class="fs-target" d="${path('target')}"/></svg>
      <div class="fs-legend"><span><i class="fs-forecast-key"></i>Forecast FTE</span><span><i class="fs-target-key"></i>Target FTE</span><small>${escape(rows[0].month)} → ${escape(last.month)}</small></div>
      <div class="fs-cost-head"><strong>12M operating cost mix</strong><span>EUR · Base plan</span></div>
      <div class="fs-cost-bar" role="img" aria-label="Personnel cost ${money(personnel)}; non-people operating expense ${money(nonPeople)}"><i style="width:${(personnel/(personnel+nonPeople||1)*100).toFixed(2)}%"></i></div>
      <div class="fs-cost-labels"><span>Personnel <strong>${money(personnel)}</strong></span><span>Non-people <strong>${money(nonPeople)}</strong></span></div>
    </div>`;
  }

  function decorate(html,source){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    const current=source.meta.end_month,plans=workforceMonths(source.workforce_forecast,current);
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();
      if(!['Integrated three-statement scenarios','Base workforce plan'].includes(title))continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      const chart=title==='Integrated three-statement scenarios'?scenarios(source.three_statement_forecast_summary):workforce(plans);
      panel.innerHTML=head.outerHTML+chart+`<details class="fs-source"><summary>View published source table</summary>${original}</details>`;
      panel.classList.add('fs-panel');
    }
    return host.innerHTML;
  }
  root.FinanceForecastStory={scenarios,workforceMonths,workforce,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers.forecast;
    renderers.forecast=function(){return decorate(before(),data);};
    document.addEventListener('click',event=>{
      const button=event.target.closest('[data-fs-metric]');if(!button)return;
      selectedMetric=button.dataset.fsMetric;render();
    });
  }
})(globalThis);
