/* Presentation-only attribution. Never allocate missing dimensions or net unlike schedules. */
(function(root){
  const pnl=['revenue','variable_production_cost','variable_selling_cost','fixed_production_cost','marginal_contribution','gross_profit','opex','depreciation','ebit','interest','tax','net_income'];
  const definitions={
    pnl:{source:'management_detail',metrics:pnl,dimensions:['entity','division'],period:'Monthly management P&L',note:'Management allocation, not a product-level legal ledger. Signed shares can exceed 100% when contributors offset.'},
    products:{source:'product_profitability',metrics:['revenue','marginal_contribution','gross_profit','opex','operating_contribution'],dimensions:['division','product_family','product'],period:'Trailing 12 months',note:'Operating product economics. No entity dimension is published; operating contribution is gross profit less allocated OPEX, not group EBIT.'},
    ar:{source:'ar_customer_aging',metrics:['total_ar','overdue_ar','overdue_90_plus'],dimensions:['entity','division','customer'],period:'Closing balance',note:'Published customer watchlist only. Shares refer to these records, NOT all group receivables. Gross balances before credit-loss allowance.'},
    inventory:{source:'inventory_sku_aging',metrics:['inventory_value','slow_moving_value','obsolescence_risk_value'],dimensions:['entity','division','product_family','product'],period:'Closing balance',note:'Published SKU watchlist only. Shares are NOT group inventory shares. Analytical stock allocation; before provisions and consolidation adjustments.'},
    ap:{source:'ap_supplier_aging',metrics:['total_ap','overdue_ap','trailing_12m_spend'],dimensions:['entity','division','supplier'],period:'Closing balance / supplier spend: trailing 12 months',note:'Published supplier watchlist only; not all group payables. Supplier spend is a flow, not the closing payable balance.'},
    capex:{source:'capex',metrics:['amount'],dimensions:['entity','division','project','event'],period:'Event month',note:'SPEND: Cash → construction in progress (CIP). GO_LIVE: CIP → property, plant & equipment (PPE), a non-cash transfer. Never add both as cash spending. No supplier or product attribution is published.'},
    cash:{source:'cash_flow_detail',metrics:['customer_collections','supplier_payments','capex','interest','tax','debt_repayment','intercompany_settlement','intercompany_treasury','operating_cash_flow','free_cash_flow','net_cash_movement'],dimensions:['entity'],period:'Monthly cash movements',note:'Positive = cash received; negative = cash paid. Legal-entity cash flows; intercompany transfers are internal, not external group income.'}
  };
  const label=s=>({pnl:'P&L',ar:'Receivables',ap:'Payables',capex:'CAPEX',opex:'OPEX',ebit:'EBIT'}[s]||s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase()));
  function records(data,key,month,event='SPEND'){
    const def=definitions[key];return (data[def.source]||[]).filter(r=>(!r.month||r.month===month)&&(key!=='capex'||r.event===event));
  }
  function aggregate(rows,metric,dimension){
    const groups=new Map();let missing=0;
    for(const r of rows){if(typeof r[metric]!=='number'||!Number.isFinite(r[metric])){missing++;continue;}
      const name=r[dimension]||'Unattributed';groups.set(name,(groups.get(name)||0)+r[metric]);}
    const total=[...groups.values()].reduce((a,b)=>a+b,0);
    return {total,missing,groups:[...groups].map(([name,value])=>({name,value,share:Math.abs(total)<1e-9?null:value/total})).sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)||a.name.localeCompare(b.name))};
  }
  const api={definitions,records,aggregate};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
  root.ContributionExplorer=api;
  const settings={};
  const e=s=>FinanceReport.escape(String(s));
  const money=v=>new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(v);
  api.pages=view=>({pnl:['pnl'],profitability:['products'],'working-capital':['ar','inventory','ap'],'operations-capex':['capex'],'cash-flow':['cash']}[view]||[]).map(key=>({title:`${label(key)} contribution`,policy:ReportContext.group,custom:true,html:`<section class="contribution-explorer" data-contribution="${key}"></section>`}));
  api.mount=data=>{
    const host=document.querySelector('[data-contribution]');if(!host)return;
    const key=host.dataset.contribution,def=definitions[key];
    document.getElementById('reportContext').textContent='Contribution explorer · independent source scope · select a bar to drill down';
    document.getElementById('viewSubtitle').textContent=`${data.meta.end_month} published close · amounts in EUR · signed contributions`;
    const months=[...new Set((data[def.source]||[]).map(r=>r.month).filter(Boolean))].sort();
    const s=settings[key]||={metric:def.metrics[0],dimension:def.dimensions[0],month:months.at(-1)||data.meta.end_month,event:'SPEND',filters:{},page:0};
    const select=(id,title,values,current)=>`<label>${e(title)}<select id="cx-${id}">${values.map(v=>`<option value="${e(v)}" ${v===current?'selected':''}>${e(label(v))}</option>`).join('')}</select></label>`;
    function paint(){
      let base=records(data,key,s.month,s.event);
      if(key==='capex'&&!base.length){const events=[...new Set((data.capex||[]).filter(r=>r.month===s.month).map(r=>r.event))];s.event=events[0]||'SPEND';base=records(data,key,s.month,s.event);}
      let rows=base.filter(r=>Object.entries(s.filters).every(([k,v])=>r[k]===v));
      const result=aggregate(rows,s.metric,s.dimension),size=innerWidth<700?3:5;
      s.page=Math.max(0,Math.min(s.page,Math.max(0,Math.ceil(result.groups.length/size)-1)));
      const visible=result.groups.slice(s.page*size,(s.page+1)*size),max=Math.max(1,...result.groups.map(g=>Math.abs(g.value)));
      host.innerHTML=`<h2>Where does ${e(label(s.metric).toLowerCase())} come from?</h2><div class="contribution-controls">${select('metric','Measure',def.metrics,s.metric)}${select('dimension','Break down by',def.dimensions,s.dimension)}${months.length?select('month','Month',months,s.month):''}${key==='capex'?select('event','Event',[...new Set((data.capex||[]).filter(r=>r.month===s.month).map(r=>r.event))],s.event):''}</div><div class="contribution-scope"><strong>${e(money(result.total))}</strong> · ${rows.length} source records · ${e(def.period)}<br>${Object.entries(s.filters).map(([k,v])=>`${e(label(k))}: ${e(v)}`).join(' / ')||'All published contributors'} <button id="cx-reset" ${Object.keys(s.filters).length?'':'disabled'}>Reset drill-down</button> <button id="cx-method">Source & coverage</button></div><div class="contribution-bars">${visible.map((g,i)=>`<button class="contribution-row" data-contributor="${i}" title="Explore ${e(g.name)}"><span>${e(g.name)}</span><span class="contribution-track"><i style="left:${g.value<0?50-Math.abs(g.value)/max*50:50}%;width:${Math.abs(g.value)/max*50}%"></i></span><span>${e(money(g.value))}<small>${g.share===null?'Share unavailable':(g.share*100).toFixed(1)+'% of selected total'}</small></span></button>`).join('')||'<p>No published records in this scope.</p>'}</div><div class="contribution-pager"><button id="cx-prev" ${s.page?'':'disabled'}>Previous contributors</button><span>${s.page+1} / ${Math.max(1,Math.ceil(result.groups.length/size))}</span><button id="cx-next" ${(s.page+1)*size>=result.groups.length?'disabled':''}>Next contributors</button></div><p class="contribution-note">${e(def.note)}${result.missing?` ${result.missing} records have unavailable measures; excluded from the sum.`:''}</p>`;
      for(const k of ['metric','dimension','month','event']){const control=document.getElementById('cx-'+k);if(control)control.onchange=()=>{s[k]=control.value;s.page=0;if(k==='month'||k==='event')s.filters={};paint();document.getElementById('cx-'+k)?.focus();};}
      document.getElementById('cx-reset').insertAdjacentHTML('beforebegin',`<button id="cx-up" ${Object.keys(s.filters).length?'':'disabled'}>Up one level</button> `);
      document.getElementById('cx-up').onclick=()=>{const dimension=Object.keys(s.filters).at(-1);delete s.filters[dimension];s.dimension=dimension;s.page=0;paint();document.getElementById('cx-dimension').focus();};
      document.getElementById('cx-reset').onclick=()=>{s.filters={};s.page=0;paint();document.getElementById('cx-dimension').focus();};
      document.getElementById('cx-prev').onclick=()=>{s.page--;paint();};document.getElementById('cx-next').onclick=()=>{s.page++;paint();};
      document.getElementById('cx-method').onclick=()=>reportDialog('Source & coverage',`<div class="help-pages"><p>Source: dashboard.json → ${e(def.source)}. ${e(def.period)} ending ${e(s.month)}. Sum of ${e(s.metric)} grouped by ${e(s.dimension)}. Signed contribution = contributor / selected total; unavailable when total is zero.</p><p>${e(def.note)} Global operating filters do not apply here: use the bars to drill into this source. No missing balance is allocated.</p></div>`);
      host.querySelectorAll('[data-contributor]').forEach(button=>button.onclick=()=>{
        const g=visible[Number(button.dataset.contributor)],next=def.dimensions.find(d=>d!==s.dimension&&!Object.hasOwn(s.filters,d));
        if(next){s.filters[s.dimension]=g.name;s.dimension=next;s.page=0;paint();document.getElementById('cx-dimension').focus();}
        else showRecords(rows.filter(r=>(r[s.dimension]||'Unattributed')===g.name));
      });
    }
    function showRecords(rows){
      let index=0,fieldPage=0;const draw=()=>{
        const entries=Object.entries(rows[index]||{}),n=innerWidth<700?3:6,part=entries.slice(fieldPage*n,(fieldPage+1)*n);
        reportDialog('Contribution source record',`<div class="row-detail">${part.map(([k,v])=>`<div><dt>${e(label(k))}</dt><dd>${e(v)}</dd></div>`).join('')}</div><p>Record ${index+1} / ${rows.length} · Fields ${fieldPage+1} / ${Math.ceil(entries.length/n)}</p><button id="cx-record-prev" ${index?'':'disabled'}>Previous record</button> <button id="cx-record-next" ${index+1<rows.length?'':'disabled'}>Next record</button> <button id="cx-fields" ${entries.length>n?'':'disabled'}>More fields</button>`);
        document.getElementById('cx-record-prev').onclick=()=>{index--;fieldPage=0;draw();};document.getElementById('cx-record-next').onclick=()=>{index++;fieldPage=0;draw();};document.getElementById('cx-fields').onclick=()=>{fieldPage=(fieldPage+1)%Math.ceil(entries.length/n);draw();};
      };draw();
    }
    paint();
  };
})(globalThis);
