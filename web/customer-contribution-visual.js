/* Source-tied customer contribution report. */
globalThis.CustomerContributionVisual = (()=>{
  let selected=null, rows=[];
  const esc=value=>FinanceReport.escape(String(value??''));
  const key=row=>`${row.entity}|${row.division}|${row.customer}`;
  const money=value=>`${Number(value)<0?'−':''}€${(Math.abs(Number(value)||0)/1e6).toFixed(2)}m`;
  const exact=value=>new Intl.NumberFormat('en-US',{style:'currency',currency:'EUR'}).format(Number(value)||0);
  const pct=value=>`${(100*(Number(value)||0)).toFixed(1)}%`;
  const sum=(items,field)=>items.reduce((n,row)=>n+(Number(row[field])||0),0);
  function page(data,state){
    rows=(data.customer_profitability||[]).filter(row=>(state.entity==='all'||row.entity===state.entity)&&(state.division==='all'||row.division===state.division)).slice().sort((a,b)=>b.operating_contribution-a.operating_contribution);
    const top=rows.slice(0,8),total=sum(rows,'operating_contribution'),max=Math.max(1,...top.map(row=>Math.abs(row.operating_contribution||0)));
    if(!rows.some(row=>key(row)===selected))selected=rows[0]?key(rows[0]):null;
    const focus=rows.find(row=>key(row)===selected);
    const chart=top.map((row,index)=>`<button type="button" class="ccv-row" data-cc-index="${index}" aria-pressed="${key(row)===selected}" aria-label="Inspect ${esc(row.customer_name)}, ${esc(exact(row.operating_contribution))} operating contribution"><span class="ccv-name"><strong>${esc(row.customer_name)}</strong><small>${esc(row.entity)} · ${esc(row.division)}</small></span><span class="ccv-track"><i class="${row.operating_contribution<0?'negative':''}" style="width:${(100*Math.abs(row.operating_contribution||0)/max).toFixed(2)}%"></i></span><b>${money(row.operating_contribution)}</b></button>`).join('');
    const options=rows.map((row,index)=>`<option value="${index}" ${key(row)===selected?'selected':''}>${esc(row.customer_name)} · ${esc(row.entity)} / ${esc(row.division)}</option>`).join('');
    const bridge=focus?`<div class="ccv-identity"><strong>${esc(focus.customer_name)}</strong><small>${esc(focus.entity)} · ${esc(focus.division)} · ${esc(focus.customer_segment)} · ${esc(focus.customer)}</small></div><div class="ccv-bridge"><span>Revenue<b>${money(focus.revenue)}</b></span><span>Marginal contribution<b>${money(focus.marginal_contribution)}</b></span><span>Gross profit<b>${money(focus.gross_profit)}</b></span><span>Allocated OPEX<b>−${money(focus.opex)}</b></span><span class="ccv-result">Operating contribution<b>${money(focus.operating_contribution)}</b></span></div><div class="ccv-ratios"><span>Gross margin <b>${pct(focus.gross_margin_pct)}</b></span><span>Contribution / revenue <b>${focus.revenue?pct(focus.operating_contribution/focus.revenue):'—'}</b></span></div><button type="button" data-cc-evidence>Inspect exact source row ↗</button>`:'<p>No customer records in this selection.</p>';
    const scope=`${state.entity==='all'?'All entities':state.entity} / ${state.division==='all'?'All divisions':state.division}`;
    return {title:'Customer profitability',custom:true,fullScreen:true,policy:ReportContext.panel('profitability','Customer profitability'),html:`<section class="ccv-board" aria-label="Customer contribution analysis"><header class="ccv-head"><div><small>Profitability / Customer economics</small><h2>Who creates operating contribution?</h2><p>Trailing 12 months · published customer allocations · ${esc(scope)}</p></div><label>Explore any customer<select data-cc-select ${rows.length?'':'disabled'}>${options}</select></label></header><div class="ccv-summary"><div><small>Customer contribution</small><strong>${money(total)}</strong><span>Sum of ${rows.length} published customer rows</span></div><div><small>Top 8 concentration</small><strong>${total?pct(sum(top,'operating_contribution')/total):'—'}</strong><span>Share of selected customer contribution</span></div><div><small>Source records</small><strong>${rows.length}</strong><span>No additional allocation inferred</span></div></div><div class="ccv-main"><section class="ccv-ranking"><div class="ccv-region-head"><h3>Largest contributors</h3><small>Click a bar · EUR million</small></div>${chart||'<p>No customer records.</p>'}<p class="ccv-note">Bars use the largest absolute contribution as scale; exact amounts are in the source row.</p></section><section class="ccv-inspector"><div class="ccv-region-head"><h3>Contribution bridge</h3><small>Selected customer</small></div>${bridge}<p class="ccv-source">Source: dashboard.json → customer_profitability. Customer OPEX is a published allocation; this view does not create one.</p></section></div></section>`};
  }
  function bind(){
    const host=document.querySelector('.ccv-board');if(!host)return;
    host.querySelectorAll('[data-cc-index]').forEach(button=>button.onclick=()=>{selected=key(rows[Number(button.dataset.ccIndex)]);render(true);});
    host.querySelector('[data-cc-select]').onchange=event=>{selected=key(rows[Number(event.target.value)]);render(true);};
    const evidence=host.querySelector('[data-cc-evidence]');if(evidence)evidence.onclick=()=>{
      const row=rows.find(item=>key(item)===selected);if(!row)return;
      const fields=[['Entity',row.entity],['Division',row.division],['Customer ID',row.customer],['Customer',row.customer_name],['Segment',row.customer_segment],['Revenue',exact(row.revenue)],['Marginal contribution',exact(row.marginal_contribution)],['Gross profit',exact(row.gross_profit)],['Allocated OPEX',exact(row.opex)],['Operating contribution',exact(row.operating_contribution)],['Calculation','Gross profit − allocated OPEX'],['Source','dashboard.json → customer_profitability']];
      reportDialog(`${row.customer_name} · customer economics`,`<dl class="row-detail">${fields.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`);
    };
  }
  return {page,bind};
})();
