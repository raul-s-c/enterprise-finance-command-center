/* Premium one-screen statement cockpits built only from published dashboard data. */
(function(root){
  const M=()=>root.FinanceReport,C=()=>root.ReportCharts;
  const esc=value=>M().escape(String(value??''));
  const sum=(rows,key)=>rows.reduce((total,row)=>total+(Number(row[key])||0),0);
  const compact=value=>M().finite(value)?`${value<0?'−':''}€${C().money(Math.abs(value))}m`:'—';
  const exactEuro=value=>M().finite(value)?`${value<-.005?'−':value>.005?'+':''}€${Math.abs(value).toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})}`:'—';
  const percent=value=>M().finite(value)?`${(value*100).toFixed(1)}%`:'—';
  const variance=(actual,prior,polarity=1)=>M().variance(actual,prior,polarity);
  const tone=value=>value?.favorable===true?'favorable':value?.favorable===false?'unfavorable':'neutral';
  const arrowIcon='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 12 12 4M6 4h6v6"/></svg>';
  const traceIcon='<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4"/><path d="m10 10 3 3"/></svg>';
  const explainIcon='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v3M8 11v3M2 8h3M11 8h3M4 4l2 2M10 10l2 2M12 4l-2 2M6 10l-2 2"/></svg>';
  const kpi=(key,label,value,change,detail,comparison)=>`<button class="sw-kpi" data-sw-focus="${key}" aria-pressed="false"><span>${esc(label)}</span><strong>${esc(value)}</strong><small class="${tone(change)}">${esc(comparison??`${C().percent(change?.relative)} vs PY`)}</small><i>${arrowIcon}</i><em>${esc(detail)}</em></button>`;
  const inspector=(key,title,value,change,formula,source,scope,route,comparison)=>`<template data-sw-detail="${key}"><div class="sw-inspector-value"><span>${esc(title)}</span><strong>${esc(value)}</strong><small class="${tone(change)}">${esc(comparison??`${C().percent(change?.relative)} vs PY`)}</small></div><dl><div><dt>Calculation</dt><dd>${esc(formula)}</dd></div><div><dt>Source</dt><dd>${esc(source)}</dd></div><div><dt>Scope</dt><dd>${esc(scope)}</dd></div><div><dt>Control</dt><dd><b class="sw-pass"></b> Reconciled to the published close</dd></div></dl><button class="sw-trace" data-story-view="${route}">Open supporting evidence</button></template>`;
  const rank=(rows,key,labelKey,filter,focus,formatter=compact)=>{const max=Math.max(...rows.map(row=>Math.abs(row[key]||0)),1);return `<div class="sw-ranking">${rows.map(row=>{const sign=(row[key]||0)<0?'negative':'positive',rowFocus=typeof focus==='function'?focus(row):(row[labelKey]==='Equity'?'equity':focus);return `<button data-sw-row="${esc(row[labelKey])}"${filter?` data-sw-filter="${filter}"`:''}${rowFocus?` data-sw-row-focus="${esc(rowFocus)}"`:''}><span>${esc(row[labelKey])}</span><strong class="${sign}">${esc(formatter(row[key],row))}</strong><i><b class="${sign}" style="width:${Math.abs(row[key]||0)/max*100}%"></b></i>${arrowIcon}</button>`;}).join('')}</div>`;};
  const shell=(title,subtitle,kpis,primary,secondary,tertiary,details)=>`<article class="statement-workspace"><header class="sw-head"><div><p>Financial performance / ${esc(title)}</p><h2>${esc(title)}</h2><span>${esc(subtitle)}</span></div><div><button data-sw-action="explain">${explainIcon}<span>Explain variance</span></button><button data-story-view="data-journey">${traceIcon}<span>Trace records</span></button></div></header><div class="sw-kpis">${kpis}</div><div class="sw-grid"><section class="sw-panel sw-primary">${primary}</section><section class="sw-panel sw-secondary">${secondary}</section><aside class="sw-panel sw-inspector"><header><span>Selected measure</span><h3>Evidence inspector</h3></header><div id="swInspectorBody"></div></aside><section class="sw-panel sw-detail">${tertiary}</section></div>${details}</article>`;
  function positiveStatementTrend(points,metricLabel,monthAttribute='data-sw-statement-month'){
    const values=points.flatMap(point=>[point.actual,point.prior]).filter(M().finite);
    if(!values.length)return '<div class="empty">No observations for this selection.</div>';
    if(values.some(value=>value<0))return C().trend(points,metricLabel,760,300).replaceAll('data-month=',`${monthAttribute}=`);
    const max=Math.max(...values,1);
    return `<div class="sw-positive-trend" role="group" aria-label="${esc(metricLabel)} actual versus prior year, EUR million; select a month for evidence">${points.map(point=>{
      const change=variance(point.actual,point.prior);
      const actual=M().finite(point.actual)?C().money(point.actual):'—',prior=M().finite(point.prior)?C().money(point.prior):'—';
      const actualHeight=M().finite(point.actual)?point.actual/max*100:0,priorHeight=M().finite(point.prior)?point.prior/max*100:0;
      return `<button type="button" class="sw-positive-month" ${monthAttribute}="${esc(point.month)}" aria-label="${esc(point.month)} ${esc(metricLabel)} actual ${actual}, prior year ${prior}, change ${esc(C().signed(change.delta))} EUR million. Show detail." title="${esc(point.month)} · AC ${actual} · PY ${prior} · Δ ${esc(C().signed(change.delta))} EUR m"><strong>${actual}</strong><span class="sw-positive-bars" aria-hidden="true"><i class="prior" style="height:${priorHeight}%"></i><i class="actual" style="height:${actualHeight}%"></i></span><small>${esc(point.month.slice(2))}</small><em class="${tone(change)}">${esc(C().signed(change.delta))}</em></button>`;
    }).join('')}</div>`;
  }
  function forecastRevenueTrend(rows,endMonth){
    const values=rows.map(row=>row.revenue_forecast).filter(M().finite);
    if(!values.length)return '<div class="empty">No forecast observations for this selection.</div>';
    if(values.some(value=>value<0))return C().series(rows,'revenue_forecast','month',endMonth,760);
    const max=Math.max(...values,1);
    return `<div class="sw-forecast-trend" role="group" aria-label="Base revenue forecast for the next twelve months, EUR million; select a month for linked statements">${rows.map(row=>{
      const value=M().finite(row.revenue_forecast)?C().money(row.revenue_forecast):'—';
      const height=M().finite(row.revenue_forecast)?row.revenue_forecast/max*100:0;
      return `<button type="button" class="sw-forecast-month" data-sw-forecast-month="${esc(row.month)}" aria-label="${esc(row.month)} Base revenue forecast ${value} EUR million. Open linked forecast statements." title="${esc(row.month)} · FC ${value} EUR m"><strong>${value}</strong><span class="sw-forecast-bars" aria-hidden="true"><i style="height:${height}%"></i></span><small>${esc(row.month.slice(2))}</small></button>`;
    }).join('')}</div>`;
  }
  function forecastMonthEvidence(rows,data){
    const cash=new Map((data.forecast_cash_flow||[]).filter(row=>row.scenario==='Base').map(row=>[row.month,row]));
    const balance=new Map((data.forecast_balance_sheet||[]).filter(row=>row.scenario==='Base').map(row=>[row.month,row]));
    const amount=value=>M().finite(value)?`${value<0?'−':''}€${C().money(Math.abs(value))}m`:'—';
    const control=value=>!M().finite(value)?'—':value===0?'€0.00':`${value<0?'−':''}€${Math.abs(value).toPrecision(6)}`;
    return rows.map(row=>{
      const cf=cash.get(row.month)||{},bs=balance.get(row.month)||{};
      return `<template data-sw-forecast-detail="${esc(row.month)}"><p class="report-note">Base scenario · ${esc(row.month)} · source-linked three-statement forecast</p><dl class="row-detail sw-forecast-detail"><div><dt>Revenue · forecast</dt><dd>${amount(row.revenue_forecast)}</dd></div><div><dt>EBIT · forecast</dt><dd>${amount(row.ebit_forecast)}</dd></div><div><dt>Free cash flow · forecast_cash_flow</dt><dd>${amount(cf.free_cash_flow)}</dd></div><div><dt>Ending cash · forecast_balance_sheet</dt><dd>${amount(bs.cash)}</dd></div><div><dt>Cash flow identity gap · EUR</dt><dd>${control(cf.cash_flow_identity_gap)}</dd></div><div><dt>Balance check · EUR</dt><dd>${control(bs.balance_check)}</dd></div></dl></template>`;
    }).join('');
  }
  function cashFlowTrend(points,metricLabel='Free cash flow',monthAttribute='data-sw-cash-month'){
    const values=points.flatMap(point=>[point.actual,point.prior]).filter(M().finite);
    if(!values.length)return '<div class="empty">No observations for this selection.</div>';
    const high=Math.max(0,...values),low=Math.min(0,...values),span=high-low||1,zero=high/span*100;
    const bar=(value,kind)=>{
      if(!M().finite(value))return '';
      const edge=value<0?'top':'bottom',offset=value<0?zero:100-zero;
      return `<i class="${kind}" style="${edge}:${offset}%;height:${Math.abs(value)/span*100}%"></i>`;
    };
    return `<div class="sw-cash-trend" role="group" aria-label="${esc(metricLabel)} actual versus prior year, EUR million; zero anchored and signed">${points.map(point=>{
      const change=variance(point.actual,point.prior);
      return `<button type="button" class="sw-cash-month" ${monthAttribute}="${esc(point.month)}" aria-label="${esc(point.month)} ${esc(metricLabel)} actual ${esc(C().signed(point.actual))}, prior year ${esc(C().signed(point.prior))}, change ${esc(C().signed(change.delta))} EUR million. Show monthly detail." title="${esc(point.month)} · AC ${esc(C().signed(point.actual))} · PY ${esc(C().signed(point.prior))} · Δ ${esc(C().signed(change.delta))} EUR m"><strong>${esc(C().signed(point.actual))}</strong><span class="sw-cash-bars" style="--cash-zero:${zero}%" aria-hidden="true">${bar(point.prior,'prior')}${bar(point.actual,'actual')}</span><small>${esc(point.month.slice(2))}</small><em class="${tone(change)}">${esc(C().signed(change.delta))}</em></button>`;
    }).join('')}</div>`;
  }
  function cashMonthEvidence(rows){
    const amount=value=>M().finite(value)?`${value<0?'−':''}€${C().money(Math.abs(value))}m`:'—';
    const control=value=>!M().finite(value)?'—':value===0?'€0.00':`${value<0?'−':''}€${Math.abs(value).toPrecision(6)}`;
    return rows.slice(-12).map(row=>{
      const identity=(row.operating_cash_flow||0)+(row.investing_cash_flow||0)-(row.free_cash_flow||0);
      return `<template data-sw-cash-detail="${esc(row.month)}"><p class="report-note">Published cash_flow · ${esc(row.month)} · consolidated group</p><dl class="row-detail sw-cash-detail"><div><dt>Operating cash flow</dt><dd>${amount(row.operating_cash_flow)}</dd></div><div><dt>Investing cash flow</dt><dd>${amount(row.investing_cash_flow)}</dd></div><div><dt>Free cash flow</dt><dd>${amount(row.free_cash_flow)}</dd></div><div><dt>Financing cash flow</dt><dd>${amount(row.financing_cash_flow)}</dd></div><div><dt>Net cash movement</dt><dd>${amount(row.net_cash_movement)}</dd></div><div><dt>OCF + investing − FCF · EUR</dt><dd>${control(identity)}</dd></div></dl></template>`;
    }).join('');
  }
  function intercompanyMonthEvidence(rows){
    return rows.slice(-12).map(row=>{
      const residual=(row.manufacturing_cost||0)+(row.transfer_pricing_markup||0)-(row.intercompany_sales||0);
      return `<template data-sw-intercompany-detail="${esc(row.month)}"><p class="report-note">Published intercompany · ${esc(row.month)} · pre-elimination group transfers</p><dl class="row-detail sw-statement-detail"><div><dt>Intercompany sales</dt><dd>${compact(row.intercompany_sales)}</dd></div><div><dt>Manufacturing cost</dt><dd>${compact(row.manufacturing_cost)}</dd></div><div><dt>Transfer-pricing markup</dt><dd>${compact(row.transfer_pricing_markup)}</dd></div><div><dt>Cost-plus rate</dt><dd>${percent(row.transfer_pricing_markup/row.manufacturing_cost)}</dd></div><div><dt>Cost + markup − sales · source rounding, EUR</dt><dd>${exactEuro(residual)}</dd></div></dl></template>`;
    }).join('');
  }
  function fxMonthEvidence(rows,scope){
    return rows.slice(-12).map(row=>{
      const residual=(row.translated_assets||0)-(row.translated_liabilities||0)-(row.translated_equity_before_cta||0)-(row.fx_translation_reserve||0);
      return `<template data-sw-fx-detail="${esc(row.month)}"><p class="report-note">Published ${esc(scope)} · ${esc(row.month)} · CTA / OCI, not transaction P&amp;L</p><dl class="row-detail sw-statement-detail"><div><dt>Translated assets</dt><dd>${compact(row.translated_assets)}</dd></div><div><dt>Translated liabilities</dt><dd>${compact(row.translated_liabilities)}</dd></div><div><dt>Equity before CTA</dt><dd>${compact(row.translated_equity_before_cta)}</dd></div><div><dt>Translation reserve · CTA</dt><dd>${compact(row.fx_translation_reserve)}</dd></div><div><dt>Assets − liabilities − equity before CTA − CTA · EUR</dt><dd>${exactEuro(residual)}</dd></div></dl></template>`;
    }).join('');
  }
  function statementMonthEvidence(rows,kind){
    const amount=value=>M().finite(value)?`${value<0?'−':''}€${C().money(Math.abs(value))}m`:'—';
    const control=value=>!M().finite(value)?'—':value===0?'€0.00':`${value<0?'−':''}€${Math.abs(value).toPrecision(6)}`;
    return rows.slice(-12).map(row=>{
      const treasury=kind==='treasury';
      const fields=treasury
        ?[['Group cash',row.cash],['Undrawn RCF',row.undrawn_rcf],['Operating minimum',row.minimum_operating_cash],['Liquidity headroom',row.liquidity_headroom],['Gross debt',row.gross_debt]]
        :[['Total assets',row.assets],['Liabilities',row.liabilities],['Equity',row.equity],['Cash',row.cash]];
      const check=treasury?row.cash+row.undrawn_rcf-row.minimum_operating_cash-row.liquidity_headroom:row.balance_check;
      const label=treasury?'Cash + undrawn RCF − minimum − headroom · EUR':'Assets − liabilities − equity · EUR';
      return `<template data-sw-statement-detail="${esc(row.month)}"><p class="report-note">Published ${treasury?'treasury_liquidity':'balance_sheet'} · ${esc(row.month)} · consolidated group</p><dl class="row-detail sw-statement-detail">${fields.map(([name,value])=>`<div><dt>${esc(name)}</dt><dd>${amount(value)}</dd></div>`).join('')}<div><dt>${label}</dt><dd>${control(check)}</dd></div></dl></template>`;
    }).join('');
  }
  function pnl(data,state){
    const rows=M().aggregate(data.management_detail,state),ac=rows.find(row=>row.month===data.meta.end_month)||{},py=rows.find(row=>row.month===M().priorMonth(data.meta.end_month))||{};
    const divisions=(data.management_detail||[]).filter(row=>row.month===data.meta.end_month&&(state.entity==='all'||row.entity===state.entity)&&(state.division==='all'||row.division===state.division)).reduce((map,row)=>{const item=map.get(row.division)||{division:row.division,revenue:0,ebit:0};item.revenue+=row.revenue||0;item.ebit+=row.ebit||0;map.set(row.division,item);return map;},new Map());
    const ranked=[...divisions.values()].sort((a,b)=>b.ebit-a.ebit),scope=`${state.entity==='all'?'All entities':state.entity} · ${state.division==='all'?'All divisions':state.division}`;
    const grossMargin=ac.gross_profit/ac.revenue,priorMargin=py.gross_profit/py.revenue;
    const cards=kpi('revenue','Revenue',compact(ac.revenue),variance(ac.revenue,py.revenue),'Recognised external revenue')+kpi('gross-profit','Gross profit',compact(ac.gross_profit),variance(ac.gross_profit,py.gross_profit),'After production cost')+kpi('gross-margin','Gross margin',M().finite(grossMargin)?`${(grossMargin*100).toFixed(1)}%`:'—',variance(grossMargin,priorMargin),'Gross profit / revenue')+kpi('ebit','EBIT',compact(ac.ebit),variance(ac.ebit,py.ebit),'Operating result')+kpi('net-income','Net income',compact(ac.net_income),variance(ac.net_income,py.net_income),'After interest and tax');
    const primary=`<div class="sw-panel-head"><div><h3>Revenue and EBIT trend</h3><small>AC / PY · EUR million · select a month</small></div><button data-story-view="performance-review">Review variances</button></div>${C().trend(M().comparisons(rows,'revenue',data.meta.end_month,12),'Revenue',760,300)}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Revenue to EBIT bridge</h3><small>Current close · no balancing plug</small></div></div>${C().waterfall(ac,false)}`;
    const tertiary=`<div class="sw-panel-head"><div><h3>EBIT contribution by division</h3><small>Selected operating scope · click a row to filter</small></div><button data-story-view="profitability">Open profitability</button></div>${rank(ranked,'ebit','division','division')}`;
    const details=inspector('revenue','Revenue',compact(ac.revenue),variance(ac.revenue,py.revenue),'Sum of management P&L revenue','management_detail',scope,'pnl')+inspector('gross-profit','Gross profit',compact(ac.gross_profit),variance(ac.gross_profit,py.gross_profit),'Revenue − variable and fixed production cost','management_detail',scope,'margin')+inspector('gross-margin','Gross margin',`${(grossMargin*100).toFixed(1)}%`,variance(grossMargin,priorMargin),'Gross profit / revenue','management_detail',scope,'margin')+inspector('ebit','EBIT',compact(ac.ebit),variance(ac.ebit,py.ebit),'Gross profit − OPEX − depreciation','management_detail',scope,'pnl')+inspector('net-income','Net income',compact(ac.net_income),variance(ac.net_income,py.net_income),'EBIT − interest − tax','management_detail',scope,'pnl');
    return {title:'Performance cockpit',custom:true,fullScreen:true,policy:root.ReportContext.card('Revenue'),html:root.PnlVisual.render(ac,py,data.meta.end_month,scope)};
  }
  function margin(data,state){
    const rows=M().aggregate(data.management_detail,state),ac=rows.find(row=>row.month===data.meta.end_month)||{},py=rows.find(row=>row.month===M().priorMonth(data.meta.end_month))||{};
    const scope=`${state.entity==='all'?'All entities':state.entity} · ${state.division==='all'?'All divisions':state.division}`;
    const rate=ac.revenue?ac.gross_profit/ac.revenue:null,priorRate=py.revenue?py.gross_profit/py.revenue:null;
    const pp=M().finite(rate)&&M().finite(priorRate)?`${((rate-priorRate)*100).toFixed(1)} pp vs PY`:'— vs PY';
    const definitions=[['mg-revenue','Revenue','revenue','Recognised external revenue'],['mg-mc','Marginal contribution','marginal_contribution','Revenue − variable production cost − variable selling cost'],['mg-gp','Gross profit','gross_profit','Marginal contribution − fixed production cost'],['mg-ebit','EBIT','ebit','Gross profit − OPEX − depreciation']];
    const cards=definitions.map(([id,title,key,formula])=>kpi(id,title,compact(ac[key]),variance(ac[key],py[key]),formula)).join('')+kpi('mg-rate','Gross margin',percent(rate),variance(rate,priorRate),'Gross profit / revenue',pp);
    const selected=(data.management_detail||[]).filter(row=>row.month===data.meta.end_month&&(state.entity==='all'||row.entity===state.entity)&&(state.division==='all'||row.division===state.division));
    const divisions=[...selected.reduce((map,row)=>{const item=map.get(row.division)||{division:row.division,marginal_contribution:0};item.marginal_contribution+=row.marginal_contribution||0;map.set(row.division,item);return map;},new Map()).values()].sort((a,b)=>b.marginal_contribution-a.marginal_contribution);
    const grossPoints=M().comparisons(rows,'gross_profit',data.meta.end_month,12);
    const grossTrend=typeof innerWidth!=='undefined'&&innerWidth>900?positiveStatementTrend(grossPoints,'Gross profit','data-month'):C().trend(grossPoints,'Gross profit',760,300);
    const primary=`<div class="sw-panel-head"><div><h3>Gross profit trend</h3><small>AC / PY · EUR million · selected operating scope · select a month</small></div><button data-story-view="pnl">Open P&amp;L</button></div>${grossTrend}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Revenue to operating result</h3><small>Variable costs → fixed production → OPEX → depreciation</small></div></div>${C().waterfall(ac,typeof innerWidth!=='undefined'&&innerWidth>900&&innerWidth<=1700,false,205)}`;
    const tertiary=`<div class="sw-panel-head"><div><h3>Marginal contribution by division</h3><small>Click a division to update the complete cockpit</small></div><button data-story-view="profitability">Explore products</button></div>${rank(divisions,'marginal_contribution','division','division')}`;
    const details=definitions.map(([id,title,key,formula])=>inspector(id,title,compact(ac[key]),variance(ac[key],py[key]),formula,'management_detail',scope,'profitability')).join('')+inspector('mg-rate','Gross margin',percent(rate),variance(rate,priorRate),'Gross profit / revenue; annual change expressed in percentage points','management_detail',scope,'profitability',pp);
    return {title:'Margin cockpit',custom:true,fullScreen:true,policy:root.ReportContext.card('Revenue'),html:shell('Margin conversion cockpit',`Explain cost conversion and where contribution is earned · ${data.meta.end_month}`,cards,primary,secondary,tertiary,details).replace('class="statement-workspace"','class="statement-workspace margin-cockpit"')};
  }
  function cash(data){
    const rows=data.cash_flow||[],ac=rows.at(-1)||{},py=rows.at(-13)||{},details=(data.cash_flow_detail||[]).filter(row=>row.month===data.meta.end_month),scope='Consolidated group';
    const cards=kpi('ocf','Operating cash flow',compact(ac.operating_cash_flow),variance(ac.operating_cash_flow,py.operating_cash_flow),'Cash generated by operations')+kpi('investing','Investing cash flow',compact(ac.investing_cash_flow),variance(ac.investing_cash_flow,py.investing_cash_flow),'Primarily CAPEX')+kpi('fcf','Free cash flow',compact(ac.free_cash_flow),variance(ac.free_cash_flow,py.free_cash_flow),'OCF + investing cash flow')+kpi('financing','Financing cash flow',compact(ac.financing_cash_flow),variance(ac.financing_cash_flow,py.financing_cash_flow),'Debt and treasury movements')+kpi('net-cash','Net cash movement',compact(ac.net_cash_movement),variance(ac.net_cash_movement,py.net_cash_movement),'Closing cash movement');
    const points=M().comparisons(rows,'free_cash_flow',data.meta.end_month,12);
    const trend=typeof innerWidth!=='undefined'&&innerWidth>900?cashFlowTrend(points):C().trend(points,'Free cash flow',760,300).replaceAll('data-month=','data-sw-cash-month=');
    const primary=`<div class="sw-panel-head"><div><h3>Free cash flow trend</h3><small>AC / PY · EUR million · signed zero · select a month</small></div><button data-story-view="treasury">Open treasury</button></div>${trend}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Cash conversion formula</h3><small>Consolidated group · source-tied close</small></div></div><div class="sw-formula"><span><small>Operating cash flow</small><strong>${compact(ac.operating_cash_flow)}</strong></span><b>+</b><span><small>Investing cash flow</small><strong>${compact(ac.investing_cash_flow)}</strong></span><b>=</b><span class="result"><small>Free cash flow</small><strong>${compact(ac.free_cash_flow)}</strong></span></div><div class="sw-flow"><span>Customer collections<strong>${compact(sum(details,'customer_collections'))}</strong></span><i>→</i><span>Operating cash flow<strong>${compact(ac.operating_cash_flow)}</strong></span><i>→</i><span>Net cash movement<strong>${compact(ac.net_cash_movement)}</strong></span></div>`;
    const entityRows=details.map(row=>({entity:row.entity,free_cash_flow:row.free_cash_flow})).sort((a,b)=>b.free_cash_flow-a.free_cash_flow);
    const tertiary=`<div class="sw-panel-head"><div><h3>Free cash flow by entity</h3><small>Legal entity contribution · click a row to filter</small></div><button data-story-view="cash-flow">Open detail</button></div>${rank(entityRows,'free_cash_flow','entity','entity')}`;
    const defs=[['ocf','Operating cash flow',ac.operating_cash_flow,py.operating_cash_flow,'Customer collections + supplier payments + interest + tax','cash_flow_detail'],['investing','Investing cash flow',ac.investing_cash_flow,py.investing_cash_flow,'Cash CAPEX and investing movements','cash_flow_detail'],['fcf','Free cash flow',ac.free_cash_flow,py.free_cash_flow,'Operating cash flow + investing cash flow','cash_flow'],['financing','Financing cash flow',ac.financing_cash_flow,py.financing_cash_flow,'Debt repayment + intercompany treasury','cash_flow_detail'],['net-cash','Net cash movement',ac.net_cash_movement,py.net_cash_movement,'OCF + investing + financing cash flow','cash_flow']];
    const evidence=defs.map(row=>inspector(row[0],row[1],compact(row[2]),variance(row[2],row[3]),row[4],row[5],scope,'cash-flow')).join('')+cashMonthEvidence(rows);
    return {title:'Cash cockpit',custom:true,fullScreen:true,policy:root.ReportContext.group,html:shell('Cash conversion cockpit',`Trace operating performance into liquidity for ${data.meta.end_month}`,cards,primary,secondary,tertiary,evidence).replace('class="statement-workspace"','class="statement-workspace cash-cockpit"')};
  }
  function balance(data){
    const rows=data.balance_sheet||[],ac=rows.at(-1)||{},py=rows.at(-13)||{},scope='Consolidated group';
    const cards=kpi('assets','Total assets',compact(ac.assets),variance(ac.assets,py.assets),'Resources controlled')+kpi('liabilities','Liabilities',compact(ac.liabilities),variance(ac.liabilities,py.liabilities,-1),'External obligations')+kpi('equity','Equity',compact(ac.equity),variance(ac.equity,py.equity),'Residual interest')+kpi('cash','Cash',compact(ac.cash),variance(ac.cash,py.cash),'Closing liquidity')+kpi('balance','Balance check',compact(ac.balance_check),{relative:null,favorable:Math.abs(ac.balance_check||0)<.1},'Assets − liabilities − equity');
    const assetsPoints=M().comparisons(rows,'assets',data.meta.end_month,12);
    const assetsChart=typeof innerWidth!=='undefined'&&innerWidth>900?positiveStatementTrend(assetsPoints,'Total assets'):C().trend(assetsPoints,'Total assets',760,300).replaceAll('data-month=','data-sw-statement-month=');
    const primary=`<div class="sw-panel-head"><div><h3>Total assets trend</h3><small>AC dark · PY gray · EUR million · select a month</small></div><button data-story-view="data-journey">Trace ledger</button></div>${assetsChart}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Balance-sheet equation</h3><small>${data.meta.end_month} · reconciled group view</small></div></div><div class="sw-formula"><span><small>Liabilities</small><strong>${compact(ac.liabilities)}</strong></span><b>+</b><span><small>Equity</small><strong>${compact(ac.equity)}</strong></span><b>=</b><span class="result"><small>Total assets</small><strong>${compact(ac.assets)}</strong></span></div><div class="sw-structure"><span>Cash<b style="width:${ac.cash/ac.assets*100}%"></b><strong>${compact(ac.cash)}</strong></span><span>Receivables<b style="width:${ac.trade_receivables/ac.assets*100}%"></b><strong>${compact(ac.trade_receivables)}</strong></span><span>Inventory<b style="width:${ac.inventory/ac.assets*100}%"></b><strong>${compact(ac.inventory)}</strong></span><span>PPE & CIP<b style="width:${(ac.ppe_gross+ac.cip+ac.accumulated_depreciation)/ac.assets*100}%"></b><strong>${compact(ac.ppe_gross+ac.cip+ac.accumulated_depreciation)}</strong></span></div>`;
    const funding=[{label:'Equity',value:ac.equity},{label:'Debt',value:ac.debt},{label:'Trade payables',value:ac.trade_payables},{label:'Contract liabilities',value:ac.contract_liabilities},{label:'Tax payable',value:ac.tax_payable}];
    const tertiary=`<div class="sw-panel-head"><div><h3>Funding structure</h3><small>Select a component to inspect its evidence</small></div><button data-story-view="treasury">Open funding</button></div>${rank(funding,'value','label',null,'liabilities')}`;
    const defs=[['assets','Total assets',ac.assets,py.assets,'Cash + net receivables + net inventory + PPE + CIP','balance_sheet'],['liabilities','Liabilities',ac.liabilities,py.liabilities,'Payables + tax + debt + contract liabilities','balance_sheet'],['equity','Equity',ac.equity,py.equity,'Share capital + retained earnings','balance_sheet'],['cash','Cash',ac.cash,py.cash,'Closing ledger cash after current-period movements','balance_sheet'],['balance','Balance check',ac.balance_check,py.balance_check,'Assets − liabilities − equity','validation']];
    const evidence=defs.map(row=>inspector(row[0],row[1],compact(row[2]),variance(row[2],row[3]),row[4],row[5],scope,'balance-sheet')).join('')+statementMonthEvidence(rows,'balance-sheet');
    return {title:'Position cockpit',custom:true,fullScreen:true,policy:root.ReportContext.group,html:shell('Financial position cockpit',`Consolidated group · understand assets, funding and balance integrity for ${data.meta.end_month}`,cards,primary,secondary,tertiary,evidence).replace('class="statement-workspace"','class="statement-workspace balance-cockpit"')};
  }
  function forecast(data){
    const base=(data.forecast||[]).filter(row=>row.scenario==='Base').sort((a,b)=>a.horizon_month-b.horizon_month),summary=data.three_statement_forecast_summary||[],baseSummary=summary.find(row=>row.scenario==='Base')||{},downSummary=summary.find(row=>row.scenario==='Downside')||{},accuracy=(data.forecast_accuracy||[]).find(row=>row.horizon_month===1)||{},nextLiquidity=(data.liquidity_forecast||[]).find(row=>row.scenario==='Base'&&row.horizon_month===1)||{},scope='Consolidated group · Base scenario';
    const revenueDelta=variance(baseSummary.revenue_12m,downSummary.revenue_12m),ebitMargin=baseSummary.ebit_12m/baseSummary.revenue_12m,fcfConversion=baseSummary.free_cash_flow_12m/baseSummary.ebit_12m;
    const cards=kpi('fc-revenue','12M revenue',compact(baseSummary.revenue_12m),revenueDelta,'Integrated Base scenario','Base · '+C().percent(revenueDelta.relative)+' vs Downside')+kpi('fc-ebit','12M EBIT',compact(baseSummary.ebit_12m),variance(baseSummary.ebit_12m,downSummary.ebit_12m),'Linked P&L','Base · '+percent(ebitMargin)+' margin')+kpi('fc-fcf','12M free cash flow',compact(baseSummary.free_cash_flow_12m),variance(baseSummary.free_cash_flow_12m,downSummary.free_cash_flow_12m),'Linked cash flow','Base · '+percent(fcfConversion)+' of EBIT')+kpi('fc-cash','Ending cash',compact(baseSummary.ending_cash_12m),variance(baseSummary.ending_cash_12m,downSummary.ending_cash_12m),'Linked balance sheet','Base · month 12')+kpi('fc-accuracy','1M forecast MAPE',percent(accuracy.mape),{relative:null,favorable:accura…7180 tokens truncated…trong></span><i>→</i><span class="result"><small>Statements</small><strong>P&amp;L · cash · balance</strong></span></div><div class="sw-flow"><span>Software NRR<strong>${percent(software.nrr)}</strong></span><i>→</i><span>Events book-to-bill<strong>${Number(events.book_to_bill||0).toFixed(2)}x</strong></span><i>→</i><span>Revenue / FTE<strong>${compact(workforce.revenue_per_fte)}</strong></span></div>`;
    const detailRows=[{label:'Software recurring mix',value:software.recurring_mix,focus:'bd-arr'},{label:'Software GRR',value:software.grr,focus:'bd-arr'},{label:'Events book-to-bill',value:events.book_to_bill,focus:'bd-backlog'},{label:'Factory headroom',value:1-util,focus:'bd-util'},{label:'Spare-parts inventory health',value:spare.length?sum(spare,'inventory_value')?spare.reduce((total,row)=>total+(row.inventory_health_pct||0)*(row.inventory_value||0),0)/sum(spare,'inventory_value'):0:0,focus:'bd-aftermarket'}];
    const tertiary=`<div class="sw-panel-head"><div><h3>Driver health</h3><small>Source-specific ratios · not a shared scale</small></div><button data-story-view="profitability">Open profitability</button></div>${rank(detailRows,'value','label',null,row=>row.focus,(value,row)=>row.label==='Events book-to-bill'?`${Number(value).toFixed(2)}x`:percent(value))}`;
    const defs=[['bd-arr','Software ARR',compact(software.arr),'Ending MRR × 12','software_summary',priorMonth],['bd-backlog','Events backlog',compact(events.ending_backlog),'Opening backlog + bookings − recognised revenue','events_summary',priorMonth],['bd-util','Factory utilization',percent(util),'Produced units / available capacity','hardware_factory_economics',factoryPriorMonth],['bd-aftermarket','Aftermarket revenue',compact(aftermarket),'Sum of close-month spare-parts revenue','spare_parts_economics',priorMonth],['bd-fte','Ending FTE',Number(workforce.ending_fte||0).toFixed(1),'Opening FTE + hires − attrition','workforce_summary',priorMonth]];
    return {title:'Driver cockpit',custom:true,fullScreen:true,policy:root.ReportContext.group,html:shell('Business driver cockpit',`Consolidated group · explain the operating causes behind the financial close for ${currentMonth}`,cards,primary,secondary,tertiary,defs.map(row=>inspector(row[0],row[1],row[2],{relative:null,favorable:true},row[3],row[4],scope,'business-drivers',`Current close · comparison vs ${row[5]}`)).join('')).replace('class="statement-workspace"','class="statement-workspace drivers-cockpit"')};
  }
  function intercompany(data){
    const rows=data.intercompany||[],ac=rows.at(-1)||{},py=rows.at(-13)||{},bs=(data.balance_sheet||[]).at(-1)||{},bsPy=(data.balance_sheet||[]).at(-13)||{},pools=(data.treasury_cash_pool||[]).map(row=>({label:`${row.source_entity} → ${row.destination_entity}`,amount:row.amount})).sort((a,b)=>b.amount-a.amount),markupRate=(ac.transfer_pricing_markup||0)/Math.max(ac.manufacturing_cost||0,1),pyMarkup=(py.transfer_pricing_markup||0)/Math.max(py.manufacturing_cost||0,1),gaps=Math.max(Math.abs(data.validation?.legal_ic_ar_ap_max_mismatch||0),Math.abs(data.validation?.consolidation_revenue_max_gap||0),Math.abs(data.validation?.consolidation_ebit_max_gap||0));
    const cards=kpi('ic-sales','Intercompany sales',compact(ac.intercompany_sales),variance(ac.intercompany_sales,py.intercompany_sales),'Transfer value before elimination')+kpi('ic-cost','Manufacturing cost',compact(ac.manufacturing_cost),variance(ac.manufacturing_cost,py.manufacturing_cost,-1),'Source-factory cost base')+kpi('ic-markup','Transfer-pricing markup',compact(ac.transfer_pricing_markup),variance(markupRate,pyMarkup),'Cost-plus amount',`${percent(markupRate)} markup rate`)+kpi('ic-reserve','Unrealized inventory profit',compact(bs.unrealized_ic_markup_reserve),variance(bs.unrealized_ic_markup_reserve,bsPy.unrealized_ic_markup_reserve,-1),'Removed until external sale')+kpi('ic-control','Consolidation gaps',compact(gaps),{relative:null,favorable:gaps<=.01},'Largest IC reconciliation difference',gaps<=.01?'All IC controls passed':'Review required');
    const transferPoints=M().comparisons(rows,'intercompany_sales',data.meta.end_month,12);
    const transferTrend=typeof innerWidth!=='undefined'&&innerWidth>900?positiveStatementTrend(transferPoints,'Intercompany sales','data-sw-intercompany-month'):C().trend(transferPoints,'Intercompany sales',760,300).replaceAll('data-month=','data-sw-intercompany-month=');
    const primary=`<div class="sw-panel-head"><div><h3>Intercompany transfer trend</h3><small>AC / PY · pre-elimination sales · EUR million · select a month</small></div><button data-story-view="operations-capex">Open factories</button></div>${transferTrend}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Cost-plus and consolidation</h3><small>Transfer pricing is visible; group profit is not overstated</small></div></div><div class="sw-formula"><span><small>Manufacturing cost</small><strong>${compact(ac.manufacturing_cost)}</strong></span><b>+</b><span><small>Cost-plus markup</small><strong>${compact(ac.transfer_pricing_markup)}</strong></span><b>=</b><span class="result"><small>Intercompany sales</small><strong>${compact(ac.intercompany_sales)}</strong></span></div><div class="sw-flow"><span>Legal-entity P&amp;L<strong>Recognised</strong></span><i>→</i><span>Group consolidation<strong>Revenue &amp; COGS eliminated</strong></span><i>→</i><span>Inventory reserve<strong>${compact(bs.unrealized_ic_markup_reserve)}</strong></span></div>`;
    const tertiary=`<div class="sw-panel-head"><div><h3>Close-month cash-pool flows</h3><small>Reciprocal treasury positions · group cash unchanged</small></div><button data-story-view="treasury">Open treasury</button></div>${rank(pools,'amount','label',null,'ic-control')}`;
    const scope='Consolidated group · legal-entity entries eliminated',defs=[['ic-sales','Intercompany sales',ac.intercompany_sales,py.intercompany_sales,'Manufacturing cost + transfer-pricing markup','intercompany'],['ic-cost','Manufacturing cost',ac.manufacturing_cost,py.manufacturing_cost,'Source-factory cost transferred to commercial entities','intercompany'],['ic-markup','Transfer-pricing markup',ac.transfer_pricing_markup,py.transfer_pricing_markup,'Intercompany sales − manufacturing cost','intercompany'],['ic-reserve','Unrealized inventory profit',bs.unrealized_ic_markup_reserve,bsPy.unrealized_ic_markup_reserve,'Markup remaining in closing inventory before external sale','balance_sheet'],['ic-control','Consolidation gaps',gaps,0,'Maximum reciprocal, revenue and EBIT consolidation gap','validation']];
    return {title:'Intercompany cockpit',custom:true,fullScreen:true,policy:root.ReportContext.group,html:shell('Intercompany & consolidation cockpit',`Follow cost-plus transfers through elimination and reserve release for ${data.meta.end_month}`,cards,primary,secondary,tertiary,defs.map(row=>inspector(row[0],row[1],compact(row[2]),variance(row[2],row[3],row[0]==='ic-cost'||row[0]==='ic-reserve'?-1:1),row[4],row[5],scope,'intercompany',row[0]==='ic-control'?(gaps<=.01?'All IC controls passed':'Review required'):undefined)).join('')+intercompanyMonthEvidence(rows))};
  }
  function fx(data,state){
    const cc=(data.constant_currency||[]).filter(row=>(state.entity==='all'||row.entity===state.entity)&&(state.division==='all'||row.division===state.division)),translation=(data.fx_translation||[]).filter(row=>row.month===data.meta.end_month&&(state.entity==='all'||row.entity===state.entity)),docs=(data.transaction_fx_close_documents||[]).filter(row=>(state.entity==='all'||row.entity===state.entity)&&(state.division==='all'||row.division===state.division)),open=docs.filter(row=>row.status==='Open');
    const revenueFx=sum(cc,'revenue_fx_effect'),ebitFx=sum(cc,'ebit_fx_effect'),cta=sum(translation,'fx_translation_reserve'),unrealized=sum(docs,'unrealized_fx_gain_loss_eur'),realized=sum(docs,'realized_fx_gain_loss_eur'),currency=[...open.reduce((map,row)=>{const item=map.get(row.transaction_currency)||{currency:row.transaction_currency,receivables:0,payables:0,exposure:0};if(row.document_type==='Receivable')item.receivables+=row.carrying_reporting_eur||0;else item.payables+=row.carrying_reporting_eur||0;item.exposure=item.receivables-item.payables;map.set(row.transaction_currency,item);return map;},new Map()).values()].sort((a,b)=>Math.abs(b.exposure)-Math.abs(a.exposure)),netExposure=sum(currency,'exposure'),summary=state.entity==='all'?(data.fx_translation_summary||[]):(data.fx_translation||[]).filter(row=>row.entity===state.entity),scope=`${state.entity==='all'?'All entities':state.entity} · ${state.division==='all'?'All divisions':state.division}`,precise=value=>Math.abs(value)<100000?`${value<0?'-':''}€${Math.abs(value/1000).toFixed(1)}k`:compact(value);
    const cards=kpi('fx-cta','Translation reserve',compact(cta),{relative:null,favorable:null},'CTA / OCI · entity scope','Separate from transaction FX')+kpi('fx-revenue','Revenue FX effect',compact(revenueFx),{relative:null,favorable:revenueFx>=0},'Reported less constant-currency revenue','Current close')+kpi('fx-ebit','EBIT FX effect',compact(ebitFx),{relative:null,favorable:ebitFx>=0},'Reported less constant-currency EBIT','Current close')+kpi('fx-docs','Open FX documents',String(open.length),{relative:null,favorable:null},'Foreign-currency AR and AP','Current close')+kpi('fx-exposure','Net transaction exposure',compact(netExposure),{relative:null,favorable:null},'Open receivables − open payables','Before hedging');
    const reservePoints=M().comparisons(summary,'fx_translation_reserve',data.meta.end_month,12);
    const reserveTrend=typeof innerWidth!=='undefined'&&innerWidth>900?cashFlowTrend(reservePoints,'Translation reserve','data-sw-fx-month'):C().trend(reservePoints,'Translation reserve',760,300).replaceAll('data-month=','data-sw-fx-month=');
    const primary=`<div class="sw-panel-head"><div><h3>Translation reserve trend</h3><small>${esc(state.entity==='all'?'Group':state.entity)} CTA / OCI · EUR million · select a month</small></div><button data-story-view="balance-sheet">Open equity</button></div>${reserveTrend}`;
    const secondary=`<div class="sw-panel-head"><div><h3>Two FX accounting paths</h3><small>Transaction remeasurement never enters CTA</small></div></div><div class="sw-dual-path"><div><span>Foreign-currency AR / AP</span><i>→</i><strong>Realized ${precise(realized)}</strong><strong>Unrealized ${precise(unrealized)}</strong><em>Transaction FX · P&amp;L</em></div><div><span>Functional-currency trial balance</span><i>→</i><strong>Assets &amp; liabilities at closing FX</strong><strong>Equity at historical rates</strong><em>Residual CTA · OCI</em></div></div>`;
    const currencyKey=row=>`fx-currency-${String(row.currency).toLowerCase()}`,tertiary=`<div class="sw-panel-head"><div><h3>Open exposure by currency</h3><small>Absolute ranking · signed receivables less payables</small></div><button data-story-view="data-journey">Trace documents</button></div>${rank(currency,'exposure','currency',null,currencyKey)}`;
    const currencyDetails=currency.map(row=>inspector(currencyKey(row),`${row.currency} net exposure`,compact(row.exposure),{relative:null,favorable:null},'Open receivables − open payables','transaction_fx_close_documents',scope,'fx',`Receivables ${compact(row.receivables)} · payables ${compact(row.payables)}`)).join(''),defs=[['fx-cta','Translation reserve',compact(cta),'Translated assets − liabilities − equity before CTA','fx_translation',`${state.entity==='all'?'All entities':state.entity} · all divisions`],['fx-revenue','Revenue FX effect',compact(revenueFx),'Reported revenue − revenue at prior-year FX','constant_currency',scope],['fx-ebit','EBIT FX effect',compact(ebitFx),'Reported EBIT − EBIT at prior-year FX','constant_currency',scope],['fx-docs','Open FX documents',String(open.length),'Count of open foreign-currency AR/AP documents','transaction_fx_close_documents',scope],['fx-exposure','Net transaction exposure',compact(netExposure),'Open foreign-currency receivables − payables','transaction_fx_close_documents',scope]];
    return {title:'FX cockpit',custom:true,fullScreen:true,policy:root.ReportContext.panel('fx','Constant-currency performance'),html:shell('FX & translation cockpit',`Separate transaction P&L, constant-currency performance and CTA for ${data.meta.end_month}`,cards,primary,secondary,tertiary,defs.map(row=>inspector(row[0],row[1],row[2],{relative:null,favorable:null},row[3],row[4],row[5],'fx',row[0]==='fx-cta'?'Entity scope · all divisions':undefined)).join('')+currencyDetails+fxMonthEvidence(summary,state.entity==='all'?'fx_translation_summary':'fx_translation'))};
  }
  function pages(view,data,state){if(view==='pnl')return [pnl(data,state)];if(view==='cash-flow')return [cash(data)];if(view==='balance-sheet')return [balance(data)];if(view==='forecast')return [forecast(data)];if(view==='macro-sensitivities')return [macro(data,state)];if(view==='treasury')return [treasury(data)];if(view==='business-drivers')return [drivers(data)];if(view==='profitability')return [profitability(data,state)];if(view==='intercompany')return [intercompany(data)];if(view==='operations-capex')return [operations(data,state)];if(view==='fx')return [fx(data,state)];return [];}
  function mount(){const body=document.getElementById('swInspectorBody');if(!body)return;const rows=()=>document.querySelectorAll('[data-sw-row]'),open=key=>{const template=document.querySelector(`template[data-sw-detail="${key}"]`);if(!template)return;body.replaceChildren(template.content.cloneNode(true));document.querySelectorAll('[data-sw-focus]').forEach(button=>button.setAttribute('aria-pressed',button.dataset.swFocus===key));body.querySelectorAll('[data-story-view]').forEach(button=>button.onclick=()=>{state.view=button.dataset.storyView;reportState.page=0;render();});};document.querySelectorAll('[data-sw-focus]').forEach(button=>button.onclick=()=>{rows().forEach(row=>row.setAttribute('aria-pressed','false'));open(button.dataset.swFocus);});rows().forEach(button=>button.onclick=()=>{const filter=button.dataset.swFilter;if(filter){state[filter]=button.dataset.swRow;reportState.page=filter==='entity'?1:0;render();return;}rows().forEach(row=>row.setAttribute('aria-pressed',row===button?'true':'false'));if(button.dataset.swRowFocus)open(button.dataset.swRowFocus);});document.querySelector('[data-sw-action="explain"]')?.addEventListener('click',()=>open(document.querySelector('[data-sw-focus][aria-pressed="true"]')?.dataset.swFocus||document.querySelector('[data-sw-focus]')?.dataset.swFocus));open(document.querySelector('[data-sw-focus]')?.dataset.swFocus);}
  const analysisFocus=new Map();
  function showFixedAssetRegister(detail){
    let query='',selectedProject='';
    const euro=value=>M().finite(Number(value))?new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(Number(value)):'—';
    const escText=value=>esc(String(value??''));
    const project=(id)=>detail.projects.find(row=>row.project===id);
    const draw=()=>{
      const selected=selectedProject?project(selectedProject):null;
      const filtered=detail.projects.filter(row=>[row.project,row.project_name,row.entity,row.division,row.status].join(' ').toLowerCase().includes(query));
      const list=filtered.map(row=>`<button type="button" class="sw-fa-project" data-sw-fa-project="${escText(row.project)}"><span><b>${escText(row.project_name)}</b><small>${escText(row.project)} · ${escText(row.entity)} / ${escText(row.division)} · ${escText(row.status)}</small></span><strong>${euro(row.project_carrying_value)}<small>project carrying value</small></strong><i>›</i></button>`).join('')||'<p class="sw-fa-empty">No projects match this search.</p>';
      const rows=selected?detail.events.filter(row=>row.project===selected.project):[];
      const trace=selected?`<div class="sw-fa-selected"><button type="button" id="sw-fa-back">← All projects</button><h3>${escText(selected.project_name)}</h3><p>${escText(selected.project)} · ${escText(selected.entity)} / ${escText(selected.division)} · ${escText(selected.status)}</p><div class="sw-fa-equation"><span><small>Cash spend to date</small><b>${euro(selected.cash_spend_ltd)}</b></span><i>→</i><span><small>Closing CIP</small><b>${euro(selected.cip_closing)}</b></span><i>→</i><span><small>Go-live transfer · non-cash</small><b>${euro(selected.go_live_transfer_ltd)}</b></span><i>→</i><span><small>Net book value</small><b>${euro(selected.net_book_value)}</b></span></div><dl class="sw-fa-fields"><div><dt>Approved budget</dt><dd>${euro(selected.budget)}</dd></div><div><dt>Gross PPE</dt><dd>${euro(selected.gross_ppe)}</dd></div><div><dt>Useful life</dt><dd>${escText(selected.useful_life_months)} months</dd></div><div><dt>Depreciation months</dt><dd>${escText(selected.depreciation_months)}</dd></div><div><dt>Modeled depreciation to date</dt><dd>${euro(selected.depreciation_ltd_modeled)}</dd></div><div><dt>Current-month depreciation · modeled</dt><dd>${euro(selected.depreciation_current_month_modeled)}</dd></div><div><dt>Capacity increase</dt><dd>${(Number(selected.capacity_increase_pct||0)*100).toFixed(1)}%</dd></div><div><dt>Depreciation source journal</dt><dd>${escText(selected.depreciation_journal_id)} · aggregated by entity</dd></div></dl><h4>Posted project events</h4><div class="sw-fa-table-wrap"><table><thead><tr><th>Month</th><th>Event</th><th>Amount</th><th>Debit account</th><th>Credit account</th><th>Source journal</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${escText(row.month)}</td><td>${escText(row.event==='SPEND'?'Cash spend':'Non-cash go-live')}</td><td>${euro(row.amount)}</td><td>${escText(row.debit_account)}</td><td>${escText(row.credit_account)}</td><td>${escText(row.journal_id)}</td></tr>`).join('')||'<tr><td colspan="6">No posted project events in the selected close.</td></tr>'}</tbody></table></div><p class="sw-fa-caveat">${escText(selected.depreciation_basis)}. No project-specific depreciation journal or individual asset ID is claimed.</p></div>`:'';
      reportDialog('CAPEX · project-to-asset lifecycle',`<div class="sw-fixed-assets"><p class="sw-fa-method">${escText(detail.evidence_basis)}</p>${selected?trace:`<label class="sw-fa-search">Find project <input id="sw-fa-search" type="search" value="${escText(query)}" placeholder="Project, entity, status…"></label><div class="sw-fa-register">${list}</div><p class="sw-fa-caveat">The project is the trace key, not a fabricated fixed-asset ID. Open projects remain in CIP; go-live moves CIP to PPE without a second cash outflow.</p>`}</div>`);
      if(selected){document.getElementById('sw-fa-back').onclick=()=>{selectedProject='';draw();};return;}
      document.getElementById('sw-fa-search').oninput=event=>{query=event.target.value.toLowerCase();draw();document.getElementById('sw-fa-search').focus();};
      document.querySelectorAll('[data-sw-fa-project]').forEach(button=>button.onclick=()=>{selectedProject=button.dataset.swFaProject;draw();});
    };
    draw();
  }
  function mountResponsive(){
    mount();
    const workspace=document.querySelector('.statement-workspace');
    if(!workspace)return;
    workspace.querySelectorAll('[data-sw-fixed-assets]').forEach(button=>button.onclick=async()=>{
      button.disabled=true;
      try{
        const response=await fetch(`data/fixed_asset_detail.json?v=${encodeURIComponent(button.dataset.version||'')}`,{cache:'force-cache'});
        if(!response.ok)throw new Error(`HTTP ${response.status}`);
        showFixedAssetRegister(await response.json());
      }catch(error){reportDialog('CAPEX asset evidence unavailable',`<p>The project asset register could not be loaded (${esc(error.message)}). The posted CAPEX schedule remains available in this report.</p>`);}
      finally{button.disabled=false;}
    });
    workspace.querySelectorAll('[data-sw-statement-month]').forEach(point=>{
      const show=()=>{
        const template=[...workspace.querySelectorAll('template[data-sw-statement-detail]')].find(item=>item.dataset.swStatementDetail===point.dataset.swStatementMonth);
        if(template)reportDialog(`${workspace.querySelector('h2')?.textContent||'Statement'} · ${point.dataset.swStatementMonth}`,`<div class="sw-statement-evidence">${template.innerHTML}</div>`);
      };
      point.addEventListener('click',show);
      if(point.tagName.toLowerCase()!=='button')point.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}});
    });
    workspace.querySelectorAll('[data-sw-cash-month]').forEach(point=>{
      const show=()=>{
        const template=[...workspace.querySelectorAll('template[data-sw-cash-detail]')].find(item=>item.dataset.swCashDetail===point.dataset.swCashMonth);
        if(template)reportDialog(`Cash flow · ${point.dataset.swCashMonth}`,`<div class="sw-cash-evidence">${template.innerHTML}</div>`);
      };
      point.addEventListener('click',show);
      if(point.tagName.toLowerCase()!=='button')point.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}});
    });
    for(const [monthAttr,detailAttr,title] of [
      ['data-sw-intercompany-month','data-sw-intercompany-detail','Intercompany cost-plus'],
      ['data-sw-fx-month','data-sw-fx-detail','Translation reserve']
    ]){
      workspace.querySelectorAll(`[${monthAttr}]`).forEach(point=>{
        const show=()=>{
          const month=point.getAttribute(monthAttr),template=[...workspace.querySelectorAll(`template[${detailAttr}]`)].find(item=>item.getAttribute(detailAttr)===month);
          if(template)reportDialog(`${title} · ${month}`,`<div class="sw-statement-evidence">${template.innerHTML}</div>`);
        };
        point.addEventListener('click',show);
        if(point.tagName.toLowerCase()!=='button')point.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}});
      });
    }
    workspace.querySelectorAll('[data-sw-forecast-month]').forEach(button=>button.onclick=()=>{
      const template=[...workspace.querySelectorAll('template[data-sw-forecast-detail]')].find(item=>item.dataset.swForecastDetail===button.dataset.swForecastMonth);
      if(template)reportDialog(`Base forecast · ${button.dataset.swForecastMonth}`,`<div class="sw-forecast-evidence">${template.innerHTML}</div>`);
    });
    const grid=workspace.querySelector('.sw-grid');
    const nav=document.createElement('nav');
    nav.className='sw-analysis-nav';nav.setAttribute('aria-label','Analysis focus');
    const panels=['primary','secondary','detail'].map(key=>workspace.querySelector(`.sw-${key}`));
    const reportKey=workspace.querySelector('h2').textContent;
    const selected=analysisFocus.get(reportKey)||0;
    if(workspace.classList.contains('margin-cockpit'))grid.classList.toggle('margin-detail-selected',selected===2);
    const labels=['Trend & drivers','Bridge & composition','Contribution & detail'];
    panels.forEach((panel,index)=>{
      panel.id=`sw-analysis-${index}`;
      const button=document.createElement('button');button.type='button';
      button.textContent=labels[index];button.setAttribute('aria-controls',panel.id);
      button.setAttribute('aria-pressed',String(index===selected));
      panel.classList.toggle('analysis-selected',index===selected);
      button.onclick=()=>{
        analysisFocus.set(reportKey,index);
        panels.forEach(p=>p.classList.toggle('analysis-selected',p===panel));
        if(workspace.classList.contains('margin-cockpit'))grid.classList.toggle('margin-detail-selected',index===2);
        nav.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
        root.VisualLayout?.positionCharts();
      };
      nav.append(button);
    });
    grid.before(nav);
    if(workspace.classList.contains('macro-cockpit'))workspace.querySelectorAll('.sw-primary [data-sw-row]').forEach(button=>button.addEventListener('click',()=>{
      const template=[...workspace.querySelectorAll('template[data-macro-identity]')].find(item=>item.dataset.macroIdentity===button.dataset.swRow);
      if(template)workspace.querySelector('.sw-secondary').innerHTML=template.innerHTML;
    }));
    workspace.addEventListener('click',event=>{
      if(!event.target.closest('[data-sw-focus],[data-sw-row-focus],[data-sw-action="explain"]'))return;
      if(window.innerWidth>1500&&!((workspace.classList.contains('cash-cockpit')||workspace.classList.contains('margin-cockpit')||workspace.classList.contains('treasury-cockpit')||workspace.classList.contains('balance-cockpit')||workspace.classList.contains('forecast-cockpit')||workspace.classList.contains('macro-cockpit')||workspace.classList.contains('drivers-cockpit'))&&window.innerWidth<=1700&&window.innerHeight<880))return;
      const body=document.getElementById('swInspectorBody');
      reportDialog('Calculation & supporting evidence',`<div class="sw-evidence-dialog">${body.innerHTML}</div>`);
      document.querySelectorAll('#reportDialogBody [data-story-view]').forEach(button=>button.onclick=()=>{
        document.getElementById('reportDialog').close();
        state.view=button.dataset.storyView;reportState.page=0;render();
      });
    });
  }
  root.StatementWorkspace={pages:(view,data,state)=>view==='margin'?[margin(data,state)]:pages(view,data,state),mount:mountResponsive};
  if(typeof module!=='undefined')module.exports={};
})(globalThis);
