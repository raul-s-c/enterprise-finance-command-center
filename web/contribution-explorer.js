/* Presentation-only attribution. Never allocate missing dimensions or net unlike schedules. */
(function(root){
  const pnl=['revenue','variable_production_cost','variable_selling_cost','fixed_production_cost','marginal_contribution','gross_profit','opex','depreciation','ebit','interest','tax','net_income'];
  const definitions={
    nwc:{source:'working_capital_contribution',metrics:['net_working_capital','gross_amount','provision','net_amount'],dimensions:['entity','division','component','contributor'],period:'Closing balance',note:'Reconciled working-capital contribution. Net external receivables plus net inventory less external trade payables equals provision-adjusted net working capital; intercompany balances remain separate.'},
    pnl:{source:'management_detail',metrics:pnl,dimensions:['entity','division'],period:'Monthly management P&L',note:'Management allocation, not a product-level legal ledger. Signed shares can exceed 100% when contributors offset.'},
    products:{source:'product_profitability',enhancedSource:'entity_product_profitability',metrics:['revenue','marginal_contribution','gross_profit','opex','operating_contribution'],enhancedMetrics:['revenue','variable_production_cost','variable_selling_cost','fixed_production_cost','marginal_contribution','gross_profit','opex','operating_contribution'],dimensions:['division','product_family','product'],enhancedDimensions:['entity','division','product_family','product_subfamily','product_type','quality_tier','product'],period:'Trailing 12 months',note:'Operating product economics. No entity dimension is published in this legacy artifact.',enhancedNote:'Operating product economics by entity and product. Operating contribution is gross profit less allocated OPEX, not product EBIT; depreciation, interest, tax and consolidation are not allocated.'},
    ar:{source:'ar_customer_aging',enhancedSource:'credit_loss_detail',metrics:['total_ar','overdue_ar','overdue_90_plus'],enhancedMetrics:['gross_ar','credit_loss_allowance','net_ar','overdue_ar','current','overdue_1_30','overdue_31_60','overdue_61_90','overdue_90_plus'],dimensions:['entity','division','customer'],enhancedDimensions:['entity','division','customer_segment','customer'],period:'Closing balance',note:'Legacy customer watchlist only; gross balances before credit-loss allowance.',enhancedNote:'Complete external customer schedule reconciled to legal trade receivables. Gross AR less expected credit-loss allowance equals legal net AR; intercompany receivables remain separate.'},
    inventory:{source:'inventory_sku_aging',enhancedSource:'inventory_provision_detail',metrics:['inventory_value','slow_moving_value','obsolescence_risk_value'],enhancedMetrics:['gross_inventory','inventory_provision','net_inventory','slow_moving_value','obsolescence_risk_value','age_0_30','age_31_60','age_61_90','age_91_180','age_180_plus'],dimensions:['entity','division','product_family','product'],enhancedDimensions:['entity','division','product_family','product_subfamily','product_type','quality_tier','generation','product'],period:'Closing balance',note:'Legacy SKU watchlist only; before provisions and consolidation adjustments.',enhancedNote:'Complete legal inventory schedule by entity and SKU. Gross inventory less obsolescence provision equals legal net inventory; the group consolidation markup reserve is separate and is not allocated to products.'},
    ap:{source:'ap_supplier_aging',metrics:['total_ap','overdue_ap','current','overdue_1_30','overdue_31_60','overdue_61_90','overdue_90_plus','trailing_12m_spend'],dimensions:['entity','division','supplier_category','supplier'],period:'Closing balance / supplier spend: trailing 12 months',note:'Complete external supplier schedule reconciled to legal trade payables. Supplier spend is a trailing-12-month flow, not the closing payable balance; intercompany payables remain separate.'},
    capex:{source:'capex',metrics:['amount'],dimensions:['entity','division','project','event'],period:'Event month',note:'SPEND: Cash → construction in progress (CIP). GO_LIVE: CIP → property, plant & equipment (PPE), a non-cash transfer. Never add both as cash spending. No supplier or product attribution is published.'},
    cash:{source:'cash_flow_detail',metrics:['customer_collections','supplier_payments','capex','interest','tax','debt_repayment','intercompany_settlement','intercompany_treasury','operating_cash_flow','free_cash_flow','net_cash_movement'],dimensions:['entity'],period:'Monthly cash movements',note:'Positive = cash received; negative = cash paid. Legal-entity cash flows; intercompany transfers are internal, not external group income.'}
  };
  const label=s=>({pnl:'P&L',ar:'Receivables',ap:'Payables',capex:'CAPEX',opex:'OPEX',ebit:'EBIT'}[s]||s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase()));
  function nwcRows(data){
    const ar=(data.credit_loss_detail||[]).map(r=>({...r,component:'Receivables',contributor:r.customer_name||r.customer,gross_amount:r.gross_ar,provision:-r.credit_loss_allowance,net_amount:r.net_ar,net_working_capital:r.net_ar}));
    const inventory=(data.inventory_provision_detail||[]).map(r=>({...r,component:'Inventory',contributor:r.product,gross_amount:r.gross_inventory,provision:-r.inventory_provision,net_amount:r.net_inventory,net_working_capital:r.net_inventory}));
    const ap=(data.ap_supplier_aging||[]).map(r=>({...r,component:'Payables',contributor:r.supplier_name||r.supplier,gross_amount:-r.total_ap,provision:0,net_amount:-r.total_ap,net_working_capital:-r.total_ap}));
    const inventoryByMonth=new Map();
    for(const row of inventory)inventoryByMonth.set(row.month,(inventoryByMonth.get(row.month)||0)+row.net_inventory);
    const consolidation=(data.working_capital||[]).map(row=>{
      const legalInventory=inventoryByMonth.get(row.month);if(!Number.isFinite(legalInventory))return null;
      const reserve=row.net_inventory-legalInventory;if(Math.abs(reserve)<0.01)return null;
      return {month:row.month,entity:'CONSOLIDATION',division:'Group',component:'Inventory',contributor:'Intercompany inventory profit reserve',gross_amount:0,provision:reserve,net_amount:reserve,net_working_capital:reserve,source_record:'working_capital.net_inventory less legal inventory subledger'};
    }).filter(Boolean);
    return [...ar,...inventory,...consolidation,...ap];
  }
  function preparedRows(data,key){return key==='nwc'?nwcRows(data):(data[source(data,key)]||[]);}
  function source(data,key){const def=definitions[key];if(key==='nwc')return def.source;return def.enhancedSource&&(data[def.enhancedSource]||[]).length?def.enhancedSource:def.source;}
  function dimensions(data,key){const def=definitions[key],rows=preparedRows(data,key);return (source(data,key)===def.enhancedSource?def.enhancedDimensions:def.dimensions).filter(d=>rows.some(r=>r[d]!==null&&r[d]!==undefined&&r[d]!==''));}
  function metrics(data,key){const def=definitions[key],rows=preparedRows(data,key);return (key==='nwc'?['net_working_capital']:source(data,key)===def.enhancedSource?def.enhancedMetrics:def.metrics).filter(m=>rows.some(r=>typeof r[m]==='number'&&Number.isFinite(r[m])));}
  function note(data,key){const def=definitions[key];return source(data,key)===def.enhancedSource&&def.enhancedNote?def.enhancedNote:def.note;}
  function records(data,key,month,event='SPEND'){
    return preparedRows(data,key).filter(r=>(!r.month||r.month===month)&&(key!=='capex'||r.event===event));
  }
  function invoiceRecords(data,month,selection=[],filters={}){
    const scope={};
    for(const field of ['entity','division','customer','customer_segment']){
      const values=[...new Set((selection||[]).map(row=>row[field]).filter(value=>value!==null&&value!==undefined&&value!==''))];
      if(values.length===1)scope[field]=values[0];
      else if(filters[field])scope[field]=filters[field];
    }
    return (data.ar_invoice_aging||[]).filter(row=>row.month===month&&Object.entries(scope).every(([field,value])=>row[field]===value));
  }
  function payableItemRecords(data,month,selection=[],filters={}){
    const scope={};
    for(const field of ['entity','division','supplier','supplier_category']){
      const values=[...new Set((selection||[]).map(row=>row[field]).filter(value=>value!==null&&value!==undefined&&value!==''))];
      if(values.length===1)scope[field]=values[0];
      else if(filters[field])scope[field]=filters[field];
    }
    return (data.ap_item_aging||[]).filter(row=>row.month===month&&Object.entries(scope).every(([field,value])=>row[field]===value));
  }
  function aggregate(rows,metric,dimension){
    const groups=new Map();let missing=0;
    for(const r of rows){if(typeof r[metric]!=='number'||!Number.isFinite(r[metric])){missing++;continue;}
      const name=r[dimension]||'Unattributed';groups.set(name,(groups.get(name)||0)+r[metric]);}
    const total=[...groups.values()].reduce((a,b)=>a+b,0);
    return {total,missing,groups:[...groups].map(([name,value])=>({name,value,share:Math.abs(total)<1e-9?null:value/total})).sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)||a.name.localeCompare(b.name))};
  }
  function ledgerEvidence(data,selection,month){
    if(!selection.length)return {scope:{},postings:[],balances:[]};
    const accounts={Receivables:'1100_AR',Payables:'2100_AP',Inventory:'1200_INVENTORY'};
    const scope={};
    for(const field of ['entity','division','component']){
      const values=[...new Set(selection.map(row=>row[field]).filter(Boolean))];
      if(values.length===1)scope[field]=values[0];
    }
    const matches=row=>row.month===month&&(!scope.entity||row.entity===scope.entity)&&(!scope.division||row.division===scope.division)&&(!scope.component||row.account===accounts[scope.component]);
    return {scope,postings:(data.working_capital_postings||[]).filter(matches),balances:(data.working_capital_rollforward||[]).filter(matches)};
  }
  const api={definitions,source,dimensions,metrics,note,records,aggregate,ledgerEvidence,invoiceRecords,payableItemRecords};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
  root.ContributionExplorer=api;
  const settings={};
  const e=s=>FinanceReport.escape(String(s??''));
  let activeContributionKey='';
  const money=v=>new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',notation:activeContributionKey==='nwc'?'compact':'standard',maximumFractionDigits:activeContributionKey==='nwc'?1:2}).format(v);
  const compactMoney=v=>new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',notation:'compact',maximumFractionDigits:1}).format(v);
  const sum=(rows,key)=>rows.reduce((total,row)=>total+(Number.isFinite(row[key])?row[key]:0),0);
  api.pages=view=>({pnl:['pnl'],profitability:['products'],'working-capital':['nwc','ar','inventory','ap'],'operations-capex':['capex'],'cash-flow':['cash']}[view]||[]).map(key=>({title:`${key==='nwc'?'Net working capital':label(key)} contribution`,policy:ReportContext.group,custom:true,contribution:true,html:`<section class="contribution-explorer" data-contribution="${key}"></section>`}));
  api.mount=data=>{
    const host=document.querySelector('[data-contribution]');if(!host)return;
    const key=host.dataset.contribution,def=definitions[key],availableDimensions=dimensions(data,key),availableMetrics=metrics(data,key),sourceName=source(data,key);
    activeContributionKey=key;
    document.getElementById('reportContext').textContent=`Contribution analysis · ${sourceName} · every displayed total is recomputed from published records`;
    document.getElementById('viewSubtitle').textContent=`${data.meta.end_month} published close · EUR · signed contributions and source lineage`;
    const months=[...new Set(preparedRows(data,key).map(r=>r.month).filter(Boolean))].sort();
    const s=settings[key]||={metric:key==='cash'&&availableMetrics.includes('free_cash_flow')?'free_cash_flow':availableMetrics[0],dimension:availableDimensions[0],month:months.at(-1)||data.meta.end_month,event:'SPEND',filters:{},page:0,selected:null,display:'value',query:''};
    if(!availableMetrics.includes(s.metric))s.metric=availableMetrics[0];if(!availableDimensions.includes(s.dimension))s.dimension=availableDimensions[0];
    const select=(id,title,values,current)=>values.length>1?`<label>${e(title)}<select id="cx-${id}">${values.map(v=>`<option value="${e(v)}" ${v===current?'selected':''}>${e(label(v))}</option>`).join('')}</select></label>`:'';
    function formula(rows,priorRows=[]){
      if(key==='pnl'&&!rows.length)return [[`Actual · ${s.month}`,'Unavailable'],[`Prior year · ${FinanceReport.priorMonth(s.month)}`,priorRows.length?sum(priorRows,s.metric):'Unavailable'],['Δ vs PY','Unavailable']];
      if(key==='pnl'&&priorRows.length){
        const actual=sum(rows,s.metric),prior=sum(priorRows,s.metric);
        return [[`Actual · ${s.month}`,actual],[`Prior year · ${FinanceReport.priorMonth(s.month)}`,prior],['Δ vs PY',actual-prior]];
      }
      if(key==='nwc')return [['Receivables',sum(rows.filter(r=>r.component==='Receivables'),'net_working_capital')],['+ Inventory',sum(rows.filter(r=>r.component==='Inventory'),'net_working_capital')],['− Payables',Math.abs(sum(rows.filter(r=>r.component==='Payables'),'net_working_capital'))],['= Net working capital',sum(rows,'net_working_capital')]];
      if(key==='ar'&&sourceName==='credit_loss_detail')return [['Gross receivables',sum(rows,'gross_ar')],['− Credit loss allowance',-sum(rows,'credit_loss_allowance')],['= Net receivables',sum(rows,'net_ar')]];
      if(key==='inventory'&&sourceName==='inventory_provision_detail')return [['Gross inventory',sum(rows,'gross_inventory')],['− Inventory provision',-sum(rows,'inventory_provision')],['= Net inventory',sum(rows,'net_inventory')]];
      if(key==='ap')return [['Trade payables',sum(rows,'total_ap')],['Overdue',sum(rows,'overdue_ap')],['Current',sum(rows,'current')]];
      if(key==='cash')return [['Operating cash flow',sum(rows,'operating_cash_flow')],['Investing / CAPEX',sum(rows,'capex')],['Free cash flow',sum(rows,'free_cash_flow')]];
      return [[label(s.metric),sum(rows,s.metric)],['Published records',String(rows.length)],['Missing measures',String(rows.filter(r=>!Number.isFinite(r[s.metric])).length)]];
    }
    function fields(rows){const preferred=['entity','division','component','contributor','customer_name','supplier_name','name','product','project_name','event',s.metric,'gross_amount','provision','net_amount','gross_ar','credit_loss_allowance','net_ar','gross_inventory','inventory_provision','net_inventory','total_ap','overdue_ap'];return [...new Set(preferred)].filter(field=>rows.some(row=>row[field]!==undefined)).slice(0,8);}
    function bridge(){
      if(key!=='nwc')return '';
      if(Object.keys(s.filters).length)return '<section class="cx-bridge"><strong>Selected-scope closing balance</strong><p>The formula and source records explain this selection. A prior-year bridge is only available for the consolidated group.</p></section>';
      const wc=data.working_capital||[],current=wc.find(r=>r.month===data.meta.end_month)||wc.at(-1)||{},prior=wc.find(r=>r.month===FinanceReport.priorMonth(data.meta.end_month))||wc.at(-13)||{};
      const values=[Number(prior.net_working_capital)||0,(Number(current.net_trade_receivables)||0)-(Number(prior.net_trade_receivables)||0),(Number(current.net_inventory)||0)-(Number(prior.net_inventory)||0),-((Number(current.trade_payables)||0)-(Number(prior.trade_payables)||0)),Number(current.net_working_capital)||0],labels=['PY','Receivables','Inventory','Payables','Actual'];
      const cumulative=[values[0],values[0]+values[1],values[0]+values[1]+values[2],values[0]+values[1]+values[2]+values[3]],all=[0,...cumulative,values[4]],max=Math.max(...all),min=Math.min(...all),span=max-min||1,y=v=>59-(v-min)/span*39;
      return `<section class="cx-bridge"><div><strong>Net working capital bridge</strong><span>PY → Actual · EUR million</span></div><svg viewBox="0 0 520 80" role="img" aria-label="Net working capital bridge from prior year to actual">${values.map((value,i)=>{const x=18+i*102,w=72;if(i===0||i===4){const top=y(value),base=y(0);return `<rect x="${x}" y="${Math.min(top,base)}" width="${w}" height="${Math.max(3,Math.abs(base-top))}" class="${i===4?'actual':'prior'}"/><text x="${x+w/2}" y="${Math.min(top,base)-4}" text-anchor="middle">${compactMoney(value)}</text><text x="${x+w/2}" y="76" text-anchor="middle" class="axis-label">${labels[i]}</text>`;}const before=cumulative[i-1],after=cumulative[i],top=Math.min(y(before),y(after)),height=Math.max(3,Math.abs(y(before)-y(after)));return `<line x1="${x-30}" y1="${y(before)}" x2="${x}" y2="${y(before)}" class="connector"/><rect x="${x}" y="${top}" width="${w}" height="${height}" class="${value>=0?'positive':'negative'}"/><text x="${x+w/2}" y="${top-4}" text-anchor="middle">${value>=0?'+':''}${compactMoney(value)}</text><text x="${x+w/2}" y="76" text-anchor="middle" class="axis-label">${labels[i]}</text>`;}).join('')}</svg></section>`;
    }
    function nwcComparison(){if(key!=='nwc')return '';const wc=data.working_capital||[],current=wc.find(r=>r.month===data.meta.end_month)||wc.at(-1),prior=wc.find(r=>r.month===FinanceReport.priorMonth(data.meta.end_month))||wc.at(-13),delta=current&&prior&&prior.net_working_capital?current.net_working_capital/prior.net_working_capital-1:null;return delta===null?'':`<em class="${delta>=0?'favorable':'unfavorable'}">${delta>=0?'+':''}${(delta*100).toFixed(1)}% vs PY</em>`;}
    function paint(){
      let base=records(data,key,s.month,s.event);if(key==='capex'&&!base.length){const events=[...new Set((data.capex||[]).filter(r=>r.month===s.month).map(r=>r.event))];s.event=events[0]||'SPEND';base=records(data,key,s.month,s.event);}
      const rows=base.filter(r=>Object.entries(s.filters).every(([field,value])=>r[field]===value)),priorRows=key==='pnl'?records(data,key,FinanceReport.priorMonth(s.month)).filter(r=>Object.entries(s.filters).every(([field,value])=>r[field]===value)):[],result=aggregate(rows,s.metric,s.dimension),size=innerHeight<=820?(key==='nwc'?2:3):innerWidth>1500?(innerHeight>1000?8:innerHeight>900?6:4):4;
      s.page=Math.max(0,Math.min(s.page,Math.max(0,Math.ceil(result.groups.length/size)-1)));const visible=result.groups.slice(s.page*size,(s.page+1)*size),max=Math.max(1,...result.groups.map(g=>Math.abs(g.value)));
      if(!s.selected||!result.groups.some(g=>g.name===s.selected))s.selected=result.groups[0]?.name||null;
      const selected=result.groups.find(g=>g.name===s.selected)||{name:'No selection',value:0,share:null},selectedRows=rows.filter(r=>(r[s.dimension]||'Unattributed')===selected.name),next=availableDimensions.find(d=>d!==s.dimension&&!Object.hasOwn(s.filters,d));
      const evidenceRows=(selectedRows.length?selectedRows:rows).filter(row=>Object.values(row).some(value=>String(value).toLowerCase().includes(s.query)));
      const evidenceKey=JSON.stringify([s.filters,s.dimension,s.selected,s.month,s.metric,s.query]);
      if(s.evidenceKey!==evidenceKey){s.evidenceKey=evidenceKey;s.evidencePage=0;}
      const evidenceSize=innerWidth>700?(innerHeight<=820?2:3):6;
      const evidencePages=Math.max(1,Math.ceil(evidenceRows.length/evidenceSize));
      s.evidencePage=Math.max(0,Math.min(s.evidencePage||0,evidencePages-1));
      const cols=fields(selectedRows.length?selectedRows:rows),evidence=evidenceRows.slice(s.evidencePage*evidenceSize,(s.evidencePage+1)*evidenceSize),flowTarget=selectedRows[0]?.contributor||selectedRows[0]?.customer_name||selectedRows[0]?.supplier_name||selectedRows[0]?.product||selectedRows[0]?.project_name||label(s.metric);
      const formulaParts=formula(rows,priorRows);
      host.innerHTML=`<header class="cx-head"><div><p>${Object.entries(s.filters).map(([field,value])=>`${e(label(field))}: ${e(value)}`).join(' / ')||'All published contributors'}</p><h2>${key==='nwc'?'Working capital contribution analysis':`Contribution analysis · ${e(label(s.metric))}`}</h2></div><div class="cx-commands"><button id="cx-method">${key==='nwc'?'Explain variance':'Explain calculation'}</button><button id="cx-trace">Trace records</button>${key==='ar'&&s.month===data.meta.end_month&&Number(data.meta.ar_invoice_count)>0?'<button id="cx-invoices" aria-label="Open invoice evidence" title="Open the reconciled invoice-level receivables schedule">Invoices</button>':''}${key==='ap'&&s.month===data.meta.end_month&&Number(data.meta.ap_item_count)>0?'<button id="cx-ap-items" aria-label="Open source accrual evidence" title="Open modeled source-accrual detail, not supplier invoices">Source accruals</button>':''}<button id="cx-change">Change dimension</button><button id="cx-export">Export selection</button></div></header><div class="cx-summary ${key==='nwc'?'nwc-summary':''}"><div><strong>${rows.length?e(money(result.total)):'Unavailable'}</strong>${nwcComparison()}<span>${rows.length} records · ${e(def.period)}</span></div>${bridge()}<div class="cx-formula">${formulaParts.map((part,index)=>`<div><span>${e(part[0])}</span><strong>${typeof part[1]==='number'?e(money(part[1])):e(part[1])}</strong></div>`).join('')}</div></div><div class="cx-toolbar"><b>Dimension:</b>${select('metric','Metric',availableMetrics,s.metric)}${months.length>1?select('month','Period',months,s.month):''}${key==='capex'?select('event','Event',[...new Set((data.capex||[]).filter(r=>r.month===s.month).map(r=>r.event))],s.event):''}<div class="cx-dimensions" aria-label="Break down by">${availableDimensions.map(d=>`<button data-dimension="${e(d)}" aria-pressed="${d===s.dimension}">${e(label(d))}</button>`).join('')}</div><div class="cx-display"><b>Show:</b><button data-display="value" aria-pressed="${s.display==='value'}">Value</button><button data-display="share" aria-pressed="${s.display==='share'}">Share</button></div></div><div class="cx-workspace"><section class="cx-ranking"><div class="cx-region-title"><h3>Contribution by ${e(label(s.dimension).toLowerCase())}</h3><span>Click to select · double-click to drill</span></div><div class="contribution-bars">${visible.map((g,i)=>`<button class="contribution-row" data-contributor="${i}" aria-pressed="${g.name===s.selected}" title="Select ${e(g.name)}"><span>${e(g.name)}</span><span>${s.display==='share'&&g.share!==null?`${(g.share*100).toFixed(1)}%`:e(money(g.value))}</span><span class="contribution-track"><i style="left:${g.value<0?50-Math.abs(g.value)/max*50:50}%;width:${Math.abs(g.value)/max*50}%"></i></span></button>`).join('')||'<p>No published records in this scope.</p>'}</div><div class="contribution-pager"><button id="cx-prev" ${s.page?'':'disabled'}>Previous</button><span>${s.page+1} / ${Math.max(1,Math.ceil(result.groups.length/size))}</span><button id="cx-next" ${(s.page+1)*size>=result.groups.length?'disabled':''}>Next</button></div></section><section class="cx-flow"><div class="cx-region-title"><h3>Value flow · ${e(selected.name)}</h3><span>Source → contributor → financial line</span></div><div class="cx-flow-map"><button><span>Published source</span><strong>${e(sourceName)}</strong></button><i>→</i><button class="selected"><span>${e(label(s.dimension))}</span><strong>${e(selected.name)}</strong></button><i>→</i><button><span>Destination</span><strong>${e(flowTarget)}</strong></button><i>→</i><button><span>Measure</span><strong>${e(label(s.metric))}</strong></button></div></section><aside class="cx-inspector"><div class="cx-region-title"><h3>Selected item details</h3><span>${e(selected.name)}</span></div><dl><div><dt>Selected value</dt><dd>${e(money(selected.value))}</dd></div><div><dt>Share of total</dt><dd>${selected.share===null?'Unavailable':`${(selected.share*100).toFixed(1)}%`}</dd></div><div><dt>Record count</dt><dd>${selectedRows.length}</dd></div><div><dt>Source table</dt><dd>${e(sourceName)}</dd></div><div><dt>Integrity</dt><dd class="favorable">● Recomputed from source</dd></div><div><dt>Drill path</dt><dd>${e([...Object.values(s.filters),selected.name].join(' › '))}</dd></div></dl><div><button id="cx-drill" ${next?'':'disabled'}>${next?`Drill to ${e(label(next))}`:'Lowest published level'}</button><button id="cx-up" ${Object.keys(s.filters).length?'':'disabled'}>Up one level</button><button id="cx-reset" ${Object.keys(s.filters).length?'':'disabled'}>Reset</button></div></aside><section class="cx-evidence"><div class="cx-region-title"><h3>Underlying evidence · ${e(selected.name)}</h3><label>Search <input id="cx-search" type="search" value="${e(s.query)}" placeholder="Customer, supplier, product…"></label></div><div class="cx-table-wrap"><table><thead><tr>${cols.map(field=>{const fullLabel=label(field),shortLabel=field==='net_working_capital'?'Net WC':fullLabel;return `<th data-field="${e(field)}" title="${e(fullLabel)}" aria-label="${e(fullLabel)}">${e(shortLabel)}</th>`;}).join('')}</tr></thead><tbody>${evidence.map(row=>`<tr>${cols.map(field=>`<td>${typeof row[field]==='number'?e(money(row[field])):e(row[field])}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section></div><p class="contribution-note">${e(note(data,key))}${result.missing?` ${result.missing} records with unavailable measures are excluded; no value is imputed.`:''}</p>`;
      host.querySelectorAll('.cx-evidence tbody tr').forEach((row,index)=>{
        row.tabIndex=0;
        row.title='Open complete published source record';
        row.setAttribute('aria-label',`Open published source record ${s.evidencePage*evidenceSize+index+1}`);
        const open=()=>showRecords([evidence[index]]);
        row.onclick=open;
        row.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();open();}};
      });
      if(key==='pnl'){
        const flow=host.querySelector('.cx-flow'),map=flow?.querySelector('.cx-flow-map'),nodes=[...map.querySelectorAll('button')],steps=[['Published source',sourceName], [label(s.dimension),selected.name], ['P&L line',label(s.metric)], ['Close period',s.month]];
        flow.querySelector('h3').textContent=`P&L lineage · ${selected.name}`;
        flow.querySelector('.cx-region-title>span').textContent='Source → entity / division → P&L line → close';
        map.classList.add('pnl-flow');
        nodes.forEach((node,index)=>{node.querySelector('span').textContent=steps[index][0];node.querySelector('strong').textContent=steps[index][1];node.setAttribute('aria-label',`${steps[index][0]}: ${steps[index][1]}`);node.classList.toggle('selected',index===2);});
        nodes[0].title='Inspect published source records';
        nodes[0].onclick=()=>document.getElementById('cx-trace').click();
        nodes[1].title=next?`Drill to ${label(next)}`:'Lowest published dimension';
        nodes[1].disabled=!next;
        nodes[1].onclick=()=>document.getElementById('cx-drill').click();
        nodes[2].title='Explain the P&L calculation';
        nodes[2].onclick=()=>document.getElementById('cx-method').click();
        nodes[3].title='Change the close period';
        nodes[3].onclick=()=>document.getElementById('cx-month')?.focus();
      }
      const evidencePanel=host.querySelector('#cx-search').closest('header');
      const evidencePager=document.createElement('span');
      evidencePager.innerHTML=`<span aria-live="polite">${evidenceRows.length?s.evidencePage*evidenceSize+1:0}–${Math.min((s.evidencePage+1)*evidenceSize,evidenceRows.length)} of ${evidenceRows.length}</span> <button id="cx-evidence-prev" aria-label="Previous evidence page" ${s.evidencePage?'':'disabled'}>‹</button> <button id="cx-evidence-next" aria-label="Next evidence page" ${s.evidencePage+1<evidencePages?'':'disabled'}>›</button>`;
      if(evidencePanel)evidencePanel.append(evidencePager);
      else host.querySelector('#cx-search').closest('label').after(evidencePager);
      if(['nwc','ar','ap','inventory'].includes(key)&&(data.working_capital_rollforward||[]).length){
        const ledgerButton=document.createElement('button');ledgerButton.id='cx-ledger';ledgerButton.textContent='Trace ledger';
        host.querySelector('.cx-commands').append(ledgerButton);
        ledgerButton.onclick=()=>{
          const component={ar:'Receivables',ap:'Payables',inventory:'Inventory'}[key];
          const selection=(selectedRows.length?selectedRows:rows).map(row=>component?{...row,component}:row);
          const evidence=ledgerEvidence(data,selection,s.month);
          const title=Object.entries(evidence.scope).map(([field,value])=>`${label(field)}: ${value}`).join(' · ')||'All legal working-capital accounts';
          reportDialog('Legal ledger evidence',`<p>${e(title)} · ${e(s.month)}</p><p>Gross legal balances, debit-positive. Customer, supplier and SKU selections do not imply invoice settlement or stock-lot attribution. Provisions and consolidation adjustments remain separate.</p><div class="row-detail">${evidence.balances.map(row=>`<div><dt>${e(row.entity)} / ${e(row.division)} / ${e(row.account)}</dt><dd>${e(compactMoney(row.opening_balance))} + ${e(compactMoney(row.debits))} − ${e(compactMoney(row.credits))} = ${e(compactMoney(row.closing_balance))}</dd></div>`).join('')||'<p>No legal ledger account exists for this selection (for example, consolidation adjustments).</p>'}</div><p>${evidence.postings.length} posted movements in this month. These explain movement, not the open-invoice population.</p><button id="cx-ledger-records" ${evidence.postings.length?'':'disabled'}>Inspect journal postings</button>`);
          document.getElementById('cx-ledger-records').onclick=()=>showRecords(evidence.postings);
        };
      }
      document.getElementById('cx-evidence-prev').onclick=()=>{s.evidencePage--;paint();};
      document.getElementById('cx-evidence-next').onclick=()=>{s.evidencePage++;paint();};
      const invoiceButton=document.getElementById('cx-invoices');
      if(invoiceButton)invoiceButton.onclick=async()=>{
        invoiceButton.disabled=true;invoiceButton.textContent='Loading…';
        try{
          const response=await fetch(`data/ar_invoice_detail.json?v=${encodeURIComponent(data.meta.version)}`,{cache:'force-cache'});
          if(!response.ok)throw new Error(`HTTP ${response.status}`);
          const detail=await response.json(),scope=invoiceRecords({ar_invoice_aging:detail.invoices},s.month,selectedRows.length?selectedRows:rows,s.filters);
          showInvoiceList(scope,detail.applications||[],detail.allocation_basis);
        }catch(error){reportDialog('Invoice evidence unavailable',`<p>The published invoice detail could not be loaded (${e(error.message)}). The customer-level AR schedule and ledger evidence remain available.</p>`);}
        finally{invoiceButton.disabled=false;invoiceButton.textContent='Invoices';}
      };
      const payableButton=document.getElementById('cx-ap-items');
      if(payableButton)payableButton.onclick=async()=>{
        payableButton.disabled=true;payableButton.textContent='Loading…';
        try{
          const response=await fetch(`data/ap_item_detail.json?v=${encodeURIComponent(data.meta.version)}`,{cache:'force-cache'});
          if(!response.ok)throw new Error(`HTTP ${response.status}`);
          const detail=await response.json(),scope=payableItemRecords({ap_item_aging:detail.items},s.month,selectedRows.length?selectedRows:rows,s.filters);
          showPayableItems(scope,detail.applications||[],detail.allocation_basis);
        }catch(error){reportDialog('Payable evidence unavailable',`<p>The published source-accrual detail could not be loaded (${e(error.message)}). The supplier-level AP schedule and ledger evidence remain available.</p>`);}
        finally{payableButton.disabled=false;payableButton.textContent='Source accruals';}
      };
      if(key==='nwc'){
        if(Object.keys(s.filters).length)host.querySelector('.cx-summary em')?.remove();
        const monthRows=records(data,key,s.month,s.event),entities=[...new Set(monthRows.map(row=>row.entity).filter(Boolean))].sort(),entity=s.filters.entity||'all';
        const divisions=[...new Set(monthRows.filter(row=>entity==='all'||row.entity===entity).map(row=>row.division).filter(Boolean))].sort();if(s.filters.division&&!divisions.includes(s.filters.division))delete s.filters.division;
        const options=(values,current,all)=>`<option value="all" ${current==='all'?'selected':''}>${all}</option>${values.map(value=>`<option value="${e(value)}" ${current===value?'selected':''}>${e(value)}</option>`).join('')}`;
        const scope=document.createElement('div');scope.className='cx-scopebar';scope.innerHTML=`<label>Entity<select id="cx-entity-scope">${options(entities,entity,'All entities')}</select></label><label>Division<select id="cx-division-scope">${options(divisions,s.filters.division||'all','All divisions')}</select></label><span id="cx-metric-slot"></span><label>Period<select disabled><option>${e(s.month)}</option></select></label>`;
        host.querySelector('.cx-summary').before(scope);const metricLabel=host.querySelector('#cx-metric')?.closest('label');if(metricLabel)document.getElementById('cx-metric-slot').replaceWith(metricLabel);
        document.getElementById('cx-entity-scope').onchange=event=>{if(event.target.value==='all')delete s.filters.entity;else s.filters.entity=event.target.value;delete s.filters.division;s.page=0;s.selected=null;paint();};
        document.getElementById('cx-division-scope').onchange=event=>{if(event.target.value==='all')delete s.filters.division;else s.filters.division=event.target.value;s.page=0;s.selected=null;paint();};
        const selectedComponents=['Receivables','Inventory','Payables'].map(component=>({component,value:sum(selectedRows.filter(row=>row.component===component),'net_working_capital')}));
        const flow=host.querySelector('.cx-flow-map');flow.classList.add('nwc-flow');flow.innerHTML=`<div class="cx-flow-column">${selectedComponents.map(item=>`<button><span>${e(item.component)}</span><strong>${e(compactMoney(item.value))}</strong></button>`).join('')}</div><button class="cx-flow-focus"><span>${e(label(s.dimension))}</span><strong>${e(selected.name)}</strong><small>${e(compactMoney(selected.value))}</small></button><div class="cx-flow-column destinations">${selectedComponents.map(item=>`<button><span>${item.component==='Receivables'?'Customers':item.component==='Payables'?'Suppliers':'Products / stock'}</span><strong>${e(compactMoney(item.value))}</strong></button>`).join('')}</div><button class="cx-flow-output"><span>Financial statement line</span><strong>Net working capital</strong><small>${e(compactMoney(selected.value))}</small></button>`;
        flow.querySelectorAll('.cx-flow-column').forEach(column=>column.querySelectorAll('button').forEach((button,index)=>{button.onclick=()=>showRecords(selectedRows.filter(row=>row.component===selectedComponents[index].component));button.disabled=!selectedRows.some(row=>row.component===selectedComponents[index].component);button.title='Inspect published component records';}));
        flow.querySelector('.cx-flow-focus').onclick=()=>document.getElementById('cx-drill').click();
        flow.querySelector('.cx-flow-output').onclick=()=>showRecords(selectedRows);
        if(innerWidth>=1101&&innerHeight<=1020){
          flow.classList.replace('nwc-flow','nwc-flow-compact');
          flow.closest('.cx-flow').querySelector('h3').textContent=`Flow · ${selected.name}`;
          flow.closest('.cx-flow').querySelector('.cx-region-title>span').textContent='Signed components sum to NWC';
          flow.innerHTML=`${selectedComponents.map(item=>`<button data-component="${e(item.component)}" ${selectedRows.some(row=>row.component===item.component)?'':'disabled'}><span>${e(item.component)} · ${item.component==='Receivables'?'Customers':item.component==='Inventory'?'Stock':'Suppliers'}</span><strong>${e(compactMoney(item.value))}</strong></button>`).join('')}<button class="cx-flow-output"><span>${e(selected.name)} · NWC</span><strong>${e(compactMoney(selected.value))}</strong></button>`;
          flow.querySelectorAll('[data-component]').forEach(button=>{button.title='Inspect published component records';button.onclick=()=>showRecords(selectedRows.filter(row=>row.component===button.dataset.component));});
          flow.querySelector('.cx-flow-output').onclick=()=>showRecords(selectedRows);
        }
        const calculation=selectedComponents.map((item,index)=>`${index&&item.value>=0?'+':''} ${compactMoney(item.value)}`).join(' ');host.querySelector('.cx-inspector dl').insertAdjacentHTML('afterbegin',`<div><dt>Calculation</dt><dd>${e(calculation)} = ${e(compactMoney(selected.value))}</dd></div>`);
      }
      for(const field of ['metric','month','event']){const control=document.getElementById('cx-'+field);if(control)control.onchange=()=>{s[field]=control.value;s.page=0;s.selected=null;if(field!=='metric')s.filters={};paint();document.getElementById('cx-'+field)?.focus();};}
      host.querySelectorAll('[data-dimension]').forEach(button=>button.onclick=()=>{s.dimension=button.dataset.dimension;s.page=0;s.selected=null;paint();});host.querySelectorAll('[data-display]').forEach(button=>button.onclick=()=>{s.display=button.dataset.display;paint();});
      host.querySelectorAll('[data-contributor]').forEach(button=>{button.onclick=()=>{s.selected=visible[Number(button.dataset.contributor)].name;paint();};button.ondblclick=()=>{s.selected=visible[Number(button.dataset.contributor)].name;if(next){s.filters[s.dimension]=s.selected;s.dimension=next;s.page=0;s.selected=null;paint();}};});
      document.getElementById('cx-drill').onclick=()=>{if(next&&s.selected){s.filters[s.dimension]=s.selected;s.dimension=next;s.page=0;s.selected=null;paint();}};document.getElementById('cx-up').onclick=()=>{const dimension=Object.keys(s.filters).at(-1);delete s.filters[dimension];s.dimension=dimension;s.page=0;s.selected=null;paint();};document.getElementById('cx-reset').onclick=()=>{s.filters={};s.page=0;s.selected=null;paint();};
      document.getElementById('cx-prev').onclick=()=>{s.page--;s.selected=null;paint();};document.getElementById('cx-next').onclick=()=>{s.page++;s.selected=null;paint();};document.getElementById('cx-search').oninput=event=>{s.query=event.target.value.toLowerCase();paint();document.getElementById('cx-search').focus();};
      document.getElementById('cx-method').onclick=()=>reportDialog(key==='nwc'?'Variance, calculation & coverage':'Calculation, source & coverage',`<div class="help-pages"><p>Source: dashboard.json → ${e(sourceName)}. ${e(def.period)} ending ${e(s.month)}. The displayed total is the exact signed sum of ${e(s.metric)} grouped by ${e(s.dimension)}.</p><p>${e(note(data,key))} Missing dimensions and measures are never allocated, replaced or balanced.</p></div>`);document.getElementById('cx-trace').onclick=()=>showRecords(selectedRows.length?selectedRows:rows);document.getElementById('cx-change').onclick=()=>{s.dimension=availableDimensions[(availableDimensions.indexOf(s.dimension)+1)%availableDimensions.length];s.page=0;s.selected=null;paint();};document.getElementById('cx-export').onclick=()=>document.getElementById('globalExport')?.click();
    }
    function sourceDetailDialog(title,body){reportDialog(title,body);const dialog=document.getElementById('reportDialog');dialog.classList.add('cx-source-detail-dialog-shell');dialog.onclose=()=>dialog.classList.remove('cx-source-detail-dialog-shell');}
    function showInvoiceList(invoiceRows,applicationRows,basis){
      let query='',page=0;const pageSize=innerWidth<700?4:6;
      const draw=()=>{
        const filtered=invoiceRows.filter(row=>[row.invoice_id,row.customer_name,row.customer,row.product,row.aging_bucket].join(' ').toLowerCase().includes(query));
        const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.max(0,Math.min(page,pages-1));
        const visibleInvoices=filtered.slice(page*pageSize,(page+1)*pageSize);
        const open=sum(invoiceRows,'open_amount'),overdue=sum(invoiceRows.filter(row=>Number(row.overdue_days)>0),'open_amount');
        const cash=sum(invoiceRows,'cash_applied_ltd'),advances=sum(invoiceRows,'advance_applied_ltd');
        const ecl=sum(invoiceRows,'credit_loss_allowance'),net=sum(invoiceRows,'net_ar');
        const cards=visibleInvoices.map(row=>`<article class="cx-invoice-card"><header><div><strong>${e(row.invoice_id)}</strong><span>${e(row.invoice_month)} · ${e(row.entity)} / ${e(row.division)}</span></div><b>${e(money(row.open_amount))}<small>gross open</small></b></header><div class="cx-invoice-meta"><span>${e(row.customer_name||row.customer)}<small>Customer</small></span><span>${e(row.product)}<small>Product</small></span><span>${e(row.aging_bucket.replaceAll('_',' '))}<small>${e(row.invoice_age_days)} days · ${e(row.overdue_days)} overdue</small></span></div><div class="cx-invoice-measures"><span>${e(money(row.invoice_amount))}<small>Invoiced</small></span><span>${e(money(row.cash_applied_ltd))}<small>Modeled cash applied</small></span><span>${e(money(row.advance_applied_ltd))}<small>Advance applied</small></span><span>${e(money(row.credit_loss_allowance))}<small>Analytical ECL</small></span><span>${e(money(row.net_ar))}<small>Analytical net AR</small></span></div><button type="button" data-cx-invoice="${e(row.invoice_id)}">Trace source and applications</button></article>`).join('')||'<p class="cx-invoice-empty">No open invoices in this selected scope.</p>';
        sourceDetailDialog('Open receivables · invoice evidence',`<div class="cx-invoice-dialog"><p class="cx-invoice-basis">${e(basis)} Posted credits are analytically allocated to invoice IDs; no bank-matched remittance is asserted. Invoice ECL is an analytical distribution of the existing customer-level provision, not a separate invoice-specific GL posting.</p><div class="cx-invoice-summary"><div><strong>${invoiceRows.length}</strong><span>Open invoices</span></div><div><strong>${e(money(open))}</strong><span>Gross open AR</span></div><div><strong>${e(money(ecl))}</strong><span>Analytical ECL</span></div><div><strong>${e(money(net))}</strong><span>Analytical net AR</span></div><div><strong>${e(money(overdue))}</strong><span>Overdue gross AR</span></div></div><div class="cx-invoice-toolbar"><label>Find invoice, customer or SKU <input id="cx-invoice-search" type="search" value="${e(query)}" placeholder="Search this scope"></label><span>${filtered.length} invoices · ${e(s.month)} close</span></div><div class="cx-invoice-cards">${cards}</div><div class="cx-invoice-pager"><button id="cx-invoice-prev" ${page?'':'disabled'}>Previous</button><span>${page+1} / ${pages}</span><button id="cx-invoice-next" ${page+1<pages?'':'disabled'}>Next</button></div></div>`);
        document.getElementById('cx-invoice-search').oninput=event=>{query=event.target.value.toLowerCase();page=0;draw();document.getElementById('cx-invoice-search').focus();};
        document.getElementById('cx-invoice-prev').onclick=()=>{page--;draw();};document.getElementById('cx-invoice-next').onclick=()=>{page++;draw();};
        document.querySelectorAll('[data-cx-invoice]').forEach(button=>button.onclick=()=>{
          const invoice=invoiceRows.find(row=>row.invoice_id===button.dataset.cxInvoice);if(!invoice)return;
          const apps=applicationRows.filter(row=>row.invoice_id===invoice.invoice_id);
          const summary=[['Invoice source ID',invoice.invoice_id],['Invoice month',invoice.invoice_month],['Customer',`${invoice.customer_name} · ${invoice.customer}`],['Product',invoice.product],['Entity / division',`${invoice.entity} / ${invoice.division}`],['Gross invoice',money(invoice.invoice_amount)],['Modeled cash applied',money(invoice.cash_applied_ltd)],['Customer advance applied',money(invoice.advance_applied_ltd)],['Gross open AR',money(invoice.open_amount)],['Analytical ECL allocation',money(invoice.credit_loss_allowance)],['Analytical net AR',money(invoice.net_ar)],['Risk multiplier',Number(invoice.risk_multiplier).toFixed(3)],['Age / overdue',`${invoice.invoice_age_days} / ${invoice.overdue_days} days`],['Aging bucket',invoice.aging_bucket.replaceAll('_',' ')]];
          const history=apps.map(row=>`<tr><td data-label="Applied month">${e(row.application_month)}</td><td data-label="Source credit journal">${e(row.source_journal_id)}</td><td data-label="Allocation type">${e(row.allocation_type.replaceAll('_',' '))}</td><td data-label="Applied">${e(money(row.applied_amount))}</td></tr>`).join('')||'<tr><td colspan="4">No allocated credits for this open invoice.</td></tr>';
          sourceDetailDialog('Invoice source trace',`<div class="cx-invoice-dialog cx-invoice-trace"><p class="cx-invoice-basis">Source invoice journal ID is preserved. Credit applications below are modeled against posted AR credits and are not bank-matched receipts. Invoice ECL is a reconciled analytical allocation of the customer schedule; the GL provision remains posted at its existing grain.</p><dl class="cx-invoice-fields">${summary.map(([field,value])=>`<div><dt>${e(field)}</dt><dd>${e(value)}</dd></div>`).join('')}</dl><h3>Posted credit allocations</h3><div class="cx-invoice-table-wrap"><table><thead><tr><th>Applied month</th><th>Source collection / advance journal</th><th>Allocation type</th><th>Applied</th></tr></thead><tbody>${history}</tbody></table></div><p>Allocation policy: ${e(basis)}</p><button id="cx-invoice-list-back" type="button">Back to invoice list</button></div>`);
          document.getElementById('cx-invoice-list-back').onclick=draw;
        });
      };
      draw();
    }
    function showPayableItems(itemRows,applicationRows,basis){
      let query='',page=0;const pageSize=innerWidth<700?4:6;
      const draw=()=>{
        const filtered=itemRows.filter(row=>[row.source_item_id,row.supplier_name,row.supplier,row.accrual_type,row.supplier_category,row.aging_bucket].join(' ').toLowerCase().includes(query));
        const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.max(0,Math.min(page,pages-1));
        const visible=filtered.slice(page*pageSize,(page+1)*pageSize);
        const open=sum(itemRows,'open_amount'),overdue=sum(itemRows.filter(row=>Number(row.overdue_days)>0),'open_amount');
        const reductions=sum(itemRows,'reductions_applied_ltd');
        const cards=visible.map(row=>`<article class="cx-invoice-card"><header><div><strong>${e(row.source_item_id)}</strong><span>${e(row.accrual_month)} · ${e(row.entity)} / ${e(row.division)}</span></div><b>${e(money(row.open_amount))}<small>gross open AP</small></b></header><div class="cx-invoice-meta"><span>${e(row.supplier_name||row.supplier)}<small>Supplier · ${e(row.supplier_category)}</small></span><span>${e(row.accrual_type.replaceAll('_',' '))}<small>Source accrual type</small></span><span>${e(row.aging_bucket.replaceAll('_',' '))}<small>${e(row.age_days)} days · ${e(row.overdue_days)} overdue</small></span></div><div class="cx-invoice-measures"><span>${e(money(row.accrual_amount))}<small>Accrued</small></span><span>${e(money(row.reductions_applied_ltd))}<small>Reductions · modeled</small></span><span>${e(row.payment_terms_days)} days<small>Payment terms</small></span></div><button type="button" data-cx-ap-item="${e(row.source_item_id)}">Trace source and reductions</button></article>`).join('')||'<p class="cx-invoice-empty">No open source accruals in this selected scope.</p>';
        sourceDetailDialog('Open payables · source accrual evidence',`<div class="cx-invoice-dialog"><p class="cx-invoice-basis">${e(basis)} Source accrual IDs are not supplier invoice numbers. AP reductions are allocated analytically from posted aggregate entries; they are not vendor-remittance matches.</p><div class="cx-invoice-summary"><div><strong>${itemRows.length}</strong><span>Open source items</span></div><div><strong>${e(money(open))}</strong><span>Gross open AP</span></div><div><strong>${e(money(overdue))}</strong><span>Overdue AP</span></div><div><strong>${e(money(reductions))}</strong><span>Reductions applied · modeled</span></div></div><div class="cx-invoice-toolbar"><label>Find accrual, supplier or type <input id="cx-ap-item-search" type="search" value="${e(query)}" placeholder="Search this scope"></label><span>${filtered.length} source items · ${e(s.month)} close</span></div><div class="cx-invoice-cards">${cards}</div><div class="cx-invoice-pager"><button id="cx-ap-item-prev" ${page?'':'disabled'}>Previous</button><span>${page+1} / ${pages}</span><button id="cx-ap-item-next" ${page+1<pages?'':'disabled'}>Next</button></div></div>`);
        document.getElementById('cx-ap-item-search').oninput=event=>{query=event.target.value.toLowerCase();page=0;draw();document.getElementById('cx-ap-item-search').focus();};
        document.getElementById('cx-ap-item-prev').onclick=()=>{page--;draw();};document.getElementById('cx-ap-item-next').onclick=()=>{page++;draw();};
        document.querySelectorAll('[data-cx-ap-item]').forEach(button=>button.onclick=()=>{
          const item=itemRows.find(row=>row.source_item_id===button.dataset.cxApItem);if(!item)return;
          const historyRows=applicationRows.filter(row=>row.accrual_journal_id===item.accrual_journal_id);
          const summary=[['Source accrual journal ID',item.accrual_journal_id],['Accrual month',item.accrual_month],['Supplier',`${item.supplier_name} · ${item.supplier}`],['Entity / division',`${item.entity} / ${item.division}`],['Accrual type / category',`${item.accrual_type} · ${item.supplier_category}`],['Original accrual',money(item.accrual_amount)],['Modeled reductions applied',money(item.reductions_applied_ltd)],['Gross open AP',money(item.open_amount)],['Age / overdue',`${item.age_days} / ${item.overdue_days} days`],['Aging bucket',item.aging_bucket.replaceAll('_',' ')],['Payment terms',`${item.payment_terms_days} days`]];
          const history=historyRows.map(row=>`<tr><td data-label="Applied month">${e(row.application_month)}</td><td data-label="Source reduction journal">${e(row.reduction_journal_id)}</td><td data-label="Reduction type">${e(row.reduction_type.replaceAll('_',' '))}</td><td data-label="Applied">${e(money(row.applied_amount))}</td></tr>`).join('')||'<tr><td colspan="4">No modeled reductions allocated to this open accrual.</td></tr>';
          sourceDetailDialog('Source accrual trace',`<div class="cx-invoice-dialog cx-invoice-trace"><p class="cx-invoice-basis">This ID is a synthetic AP accrual journal ID, not a supplier invoice number. Reduction applications are modeled from aggregate AP postings; no remittance or invoice matching is claimed.</p><dl class="cx-invoice-fields">${summary.map(([field,value])=>`<div><dt>${e(field)}</dt><dd>${e(value)}</dd></div>`).join('')}</dl><h3>Modeled AP reduction allocations</h3><div class="cx-invoice-table-wrap"><table><thead><tr><th>Applied month</th><th>Source reduction journal</th><th>Reduction type</th><th>Applied</th></tr></thead><tbody>${history}</tbody></table></div><p>Allocation policy: ${e(basis)}</p><button id="cx-ap-item-list-back" type="button">Back to source items</button></div>`);
          document.getElementById('cx-ap-item-list-back').onclick=draw;
        });
      };
      draw();
    }
    function showRecords(rows){let index=0,fieldPage=0;const draw=()=>{const entries=Object.entries(rows[index]||{}),n=innerWidth<700?3:6,part=entries.slice(fieldPage*n,(fieldPage+1)*n);reportDialog('Published source record',`<div class="row-detail">${part.map(([field,value])=>`<div><dt>${e(label(field))}</dt><dd>${e(value)}</dd></div>`).join('')}</div><p>Record ${index+1} / ${rows.length} · Fields ${fieldPage+1} / ${Math.max(1,Math.ceil(entries.length/n))}</p><button id="cx-record-prev" ${index?'':'disabled'}>Previous record</button> <button id="cx-record-next" ${index+1<rows.length?'':'disabled'}>Next record</button> <button id="cx-fields" ${entries.length>n?'':'disabled'}>More fields</button>`);document.getElementById('cx-record-prev').onclick=()=>{index--;fieldPage=0;draw();};document.getElementById('cx-record-next').onclick=()=>{index++;fieldPage=0;draw();};document.getElementById('cx-fields').onclick=()=>{fieldPage=(fieldPage+1)%Math.ceil(entries.length/n);draw();};};draw();}
    paint();
  };
})(globalThis);
