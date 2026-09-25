/* Portfolio watch over published SKU economics; rounding remains visible. */
globalThis.SkuProfitabilityWatch=(()=>{
  let selected=null,rows=[],catalog=[];
  const esc=value=>FinanceReport.escape(String(value??''));
  const key=row=>`${row.division}|${row.product}`;
  const money=value=>{const n=Number(value)||0,a=Math.abs(n);return `${n<0?'−':''}€${a>=1e6?(a/1e6).toFixed(2)+'m':a>=1e3?(a/1e3).toFixed(1)+'k':a.toFixed(0)}`;};
  const exact=value=>new Intl.NumberFormat('en-US',{style:'currency',currency:'EUR'}).format(Number(value)||0);
  const pct=value=>`${(100*(Number(value)||0)).toFixed(1)}%`;
  const residuals=row=>({
    mc:row.revenue-row.variable_production_cost-row.variable_selling_cost-row.marginal_contribution,
    gp:row.marginal_contribution-row.fixed_production_cost-row.gross_profit,
    op:row.gross_profit-row.opex-row.operating_contribution
  });
  function page(data,state){
    rows=(data.product_profitability||[]).filter(row=>state.division==='all'||row.division===state.division).slice().sort((a,b)=>a.operating_contribution-b.operating_contribution);
    catalog=(data.product_catalog||[]).filter(row=>state.division==='all'||row.division===state.division);
    if(!rows.some(row=>key(row)===selected))selected=rows[0]?key(rows[0]):null;
    const focus=rows.find(row=>key(row)===selected),watch=rows.slice(0,8),max=Math.max(1,...watch.map(row=>Math.abs(row.operating_contribution||0)));
    const negative=rows.filter(row=>row.operating_contribution<0).length;
    const withRevenue=rows.filter(row=>Number(row.revenue)>0);
    const minMargin=withRevenue.length?Math.min(...withRevenue.map(row=>row.operating_contribution/row.revenue)):null;
    const chart=watch.map((row,index)=>`<button type="button" class="spw-row" data-spw-index="${index}" aria-pressed="${key(row)===selected}" aria-label="Inspect ${esc(row.name)}, ${esc(exact(row.operating_contribution))} operating contribution"><span class="spw-name"><strong>${esc(row.name)}</strong><small>${esc(row.division)} · ${esc(row.product)}</small></span><span class="spw-track"><i class="${row.operating_contribution<0?'negative':''}" style="width:${(100*Math.abs(row.operating_contribution||0)/max).toFixed(2)}%"></i></span><b>${money(row.operating_contribution)}</b></button>`).join('');
    const options=rows.map((row,index)=>`<option value="${index}" ${key(row)===selected?'selected':''}>${esc(row.name)} · ${esc(row.product)}</option>`).join('');
    const bridge=focus?`<div class="spw-identity"><strong>${esc(focus.name)}</strong><small>${esc(focus.division)} · ${esc(focus.product_family)} · ${esc(focus.quality_tier)} · ${esc(focus.product)}</small></div><div class="spw-bridge"><span>Revenue<b>${money(focus.revenue)}</b></span><span>Variable production cost<b>−${money(focus.variable_production_cost)}</b></span><span>Variable selling cost<b>−${money(focus.variable_selling_cost)}</b></span><span>Marginal contribution<b>${money(focus.marginal_contribution)}</b></span><span>Fixed production cost<b>−${money(focus.fixed_production_cost)}</b></span><span>Gross profit<b>${money(focus.gross_profit)}</b></span><span>Allocated OPEX<b>−${money(focus.opex)}</b></span><span class="spw-result">Operating contribution<b>${money(focus.operating_contribution)}</b></span></div><div class="spw-actions"><button type="button" data-spw-evidence>Exact source and rounding ↗</button><button type="button" data-spw-catalog>Catalog structure ↗</button></div>`:'<p>No SKU economics in this division.</p>';
    const html=`<section class="spw-board" aria-label="SKU profitability watch"><header class="spw-head"><div><small>Profitability / Product economics</small><h2>Which SKUs need attention?</h2><p>Trailing 12 months · published product allocation · ${esc(state.division==='all'?'All divisions':state.division)}</p></div><label>Explore any SKU<select data-spw-select ${rows.length?'':'disabled'}>${options}</select></label></header><div class="spw-summary"><div><small>Published SKUs</small><strong>${rows.length}</strong><span>Within the selected division</span></div><div><small>Negative contribution</small><strong>${negative}</strong><span>Below zero; never inferred</span></div><div><small>Lowest operating margin</small><strong>${minMargin===null?'—':pct(minMargin)}</strong><span>Operating contribution / revenue</span></div></div><div class="spw-main"><section class="spw-ranking"><div class="spw-region-head"><h3>Lowest operating contribution</h3><small>Click a bar · published EUR</small></div>${chart||'<p>No SKU records.</p>'}<p class="spw-note">Bars are scaled within these eight source rows; no zero or loss is implied by a short bar.</p></section><section class="spw-inspector"><div class="spw-region-head"><h3>Product cost bridge</h3><small>Selected SKU</small></div>${bridge}<p class="spw-source">Source: product_profitability · published allocation. Component rounding is disclosed in exact evidence.</p></section></div></section>`;
    return {title:'SKU profitability',custom:true,fullScreen:true,policy:ReportContext.panel('profitability','SKU profitability'),html};
  }
  function bind(){
    const host=document.querySelector('.spw-board');if(!host)return;
    host.querySelectorAll('[data-spw-index]').forEach(button=>button.onclick=()=>{selected=key(rows[Number(button.dataset.spwIndex)]);render(true);});
    host.querySelector('[data-spw-select]').onchange=event=>{selected=key(rows[Number(event.target.value)]);render(true);};
    const evidence=host.querySelector('[data-spw-evidence]');if(evidence)evidence.onclick=()=>{
      const row=rows.find(item=>key(item)===selected);if(!row)return;
      const residual=residuals(row);
      const fields=[['Division',row.division],['SKU',row.product],['Product',row.name],['Family',row.product_family],['Subfamily',row.product_subfamily],['Quality tier',row.quality_tier],['Units',row.quantity],['Revenue',exact(row.revenue)],['Variable production cost',exact(row.variable_production_cost)],['Variable selling cost',exact(row.variable_selling_cost)],['Marginal contribution',exact(row.marginal_contribution)],['MC source rounding residual',exact(residual.mc)],['Fixed production cost',exact(row.fixed_production_cost)],['Gross profit',exact(row.gross_profit)],['GP source rounding residual',exact(residual.gp)],['Allocated OPEX',exact(row.opex)],['Operating contribution',exact(row.operating_contribution)],['Operating source rounding residual',exact(residual.op)],['Source','dashboard.json → product_profitability']];
      reportDialog(`${row.product} · product economics`,`<dl class="row-detail">${fields.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><p>Residual = preceding published components minus the published subtotal; no balancing adjustment is made.</p>`);
    };
    const browse=host.querySelector('[data-spw-catalog]');if(browse)browse.onclick=()=>{
      reportDialog('Catalog structure',`<p>${catalog.length} published division / family / subfamily / quality-tier records · source: dashboard.json → product_catalog.</p><dl class="row-detail">${catalog.map(row=>`<div><dt>${esc(row.division)} · ${esc(row.product_family)} / ${esc(row.product_subfamily)} · ${esc(row.quality_tier)}</dt><dd>${esc(row.sku_count)} SKUs · ${esc(row.initially_active_skus)} initially active</dd></div>`).join('')}</dl>`);
    };
  }
  return {page,bind,residuals};
})();
