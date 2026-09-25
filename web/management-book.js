/* Enterprise management book: one-screen narrative, evidence and action. */
(function(root){
  const M=()=>root.FinanceReport,C=()=>root.ReportCharts;
  const esc=v=>M().escape(String(v??'')),money=v=>C().money(v),pct=v=>M().finite(v)?`${(v*100).toFixed(1)}%`:'—';
  const tone=v=>v?.favorable===true?'favorable':v?.favorable===false?'unfavorable':'neutral';
  let executiveRegionIndex=0;
  function kpi(key,label,value,delta,route,note){
    const comparison=note||(delta?.relative===null?'No comparable':`${C().percent(delta?.relative)} vs PY`);
    return `<button class="story-kpi" data-story-focus="${key}" data-story-view-route="${route}" aria-pressed="false"><span>${esc(label)}</span><strong>${esc(value)}</strong><small class="${tone(delta)}">${esc(comparison)}</small><i aria-hidden="true">↗</i></button>`;
  }
  function actionRail(data){
    const active=(data.management_actions||[]).filter(a=>['Open','In Progress'].includes(a.status)).sort((a,b)=>a.priority.localeCompare(b.priority)||a.due_month.localeCompare(b.due_month)).slice(0,3);
    return `<section class="tower-actions"><div class="story-region-head"><div><h3>Management priorities</h3><small>Owner, due date and current lifecycle</small></div><button data-story-view="action-execution">View all</button></div>${active.map((a,i)=>`<button class="story-action" data-action-id="${esc(a.action_id)}"><b>${i+1}</b><span><strong>${esc(a.trigger_metric)}</strong><small>${esc(a.action)}</small><em>${esc(a.owner_role)} · due ${esc(a.due_month)}</em></span><i class="${a.overdue?'unfavorable':a.status==='In Progress'?'favorable':''}">${esc(a.status)}</i></button>`).join('')}</section>`;
  }
  function storyLine(data){
    const actual=(data.actual||[]).slice(-36),w=1000,vals=actual.map(r=>r.revenue),min=Math.min(...vals),max=Math.max(...vals),span=max-min||1;
    const points=actual.map((r,i)=>`${i/(actual.length-1)*w},${10+(max-r.revenue)/span*26}`).join(' '),milestones=[];
    const cap=(data.capex||[]).find(r=>r.event==='GO_LIVE');if(cap)milestones.push([cap.month,cap.project_name,'Factory go-live']);
    const phase=(data.portfolio_events||[]).find(r=>r.event==='PHASE_OUT_APPROVED');if(phase)milestones.push([phase.month,phase.product,'Portfolio decision']);
    const act=(data.management_actions||[]).find(a=>['Open','In Progress'].includes(a.status));if(act)milestones.push([act.opened_month,act.trigger_metric,'Recovery action']);
    return `<section class="story-timeline"><div class="story-region-head"><div><h3>36-month company story</h3><small>Close history and management events</small></div><button data-story-view="data-journey">Trace data</button></div><svg viewBox="0 0 ${w} 40" preserveAspectRatio="none" role="img" aria-label="36 month revenue history"><polyline points="${points}" fill="none" stroke="#25282c" stroke-width="2"/></svg><div class="story-milestones">${milestones.map(m=>`<span><b>${esc(m[0])}</b>${esc(m[2])} · ${esc(m[1])}</span>`).join('')}</div></section>`;
  }
  function miniScale(values){
    const finite=values.filter(M().finite),min=Math.min(0,...finite),max=Math.max(0,...finite),span=max-min||1,zero=-min/span*100;
    return {zero,bar:value=>{if(!M().finite(value))return 'display:none';const point=(value-min)/span*100;return `bottom:${Math.min(point,zero)}%;height:${Math.abs(point-zero)}%`;}};
  }
  function desktopCanvas(){return typeof innerWidth==='undefined'||innerWidth>900;}
  function executiveMiniTrend(rows,endMonth,overview=false){
    const metric=overview?'revenue':typeof reportState!=='undefined'&&reportState.metric==='ebit'?'ebit':'revenue',title=metric==='ebit'?'EBIT':'Revenue',points=M().comparisons(rows,metric,endMonth,12),scale=miniScale(points.flatMap(point=>[point.actual,point.prior]));
    const header=overview?`<h3>Revenue · Actual vs prior year</h3><small>AC dark · PY gray · EUR million · select a month</small>`:`<h3>${title} performance</h3><small>AC dark · PY gray · EUR million · select a month</small>`;
    const action=overview?'<button data-story-view="pnl">View P&amp;L</button>':`<div class="metric-toggle" aria-label="Chart metric"><button data-metric="revenue" aria-pressed="${metric==='revenue'}">Revenue</button><button data-metric="ebit" aria-pressed="${metric==='ebit'}">EBIT</button></div>`;
    return `<section class="story-region story-wide executive-mini-trend story-trend"><div class="story-region-head"><div>${header}</div>${action}</div><div class="executive-mini-months">${points.map(point=>`<button class="executive-mini-month" data-month="${esc(point.month)}" aria-label="${esc(point.month)} ${title} actual ${money(point.actual)}, prior year ${money(point.prior)} EUR million. Show detail." title="${esc(point.month)} · AC ${money(point.actual)} · PY ${money(point.prior)} EUR m"><strong>${money(point.actual)}</strong><span class="executive-mini-bars" style="--zero:${scale.zero}%"><i class="prior" style="${scale.bar(point.prior)}"></i><i class="actual" style="${scale.bar(point.actual)}"></i></span><small>${esc(point.month.slice(2))}</small></button>`).join('')}</div></section>`;
  }
  function executiveMiniForecast(rows){
    const scale=miniScale(rows.map(row=>row.revenue_forecast));
    return `<div class="executive-forecast-months" role="img" aria-label="Base revenue forecast for the next twelve months, EUR million, signed zero baseline">${rows.map(row=>`<div class="executive-forecast-month" title="${esc(row.month)} · FC ${money(row.revenue_forecast)} EUR m"><strong>${money(row.revenue_forecast)}</strong><span class="executive-forecast-bars" style="--zero:${scale.zero}%"><i style="${scale.bar(row.revenue_forecast)}"></i></span><small>${esc(row.month.slice(2))}</small></div>`).join('')}</div>`;
  }
  function contribution(data,state){
    const divisions=[...new Set((data.management_detail||[]).map(row=>row.division))].filter(division=>state.division==='all'||division===state.division).map(division=>({...M().aggregate(data.management_detail,{...state,division}).find(row=>row.month===data.meta.end_month),division})).filter(row=>M().finite(row.ebit)).sort((a,b)=>b.ebit-a.ebit),dmax=Math.max(...divisions.map(d=>Math.abs(d.ebit)),1);
    return `<section class="tower-contribution"><div class="story-region-head"><div><h3>EBIT contribution by division</h3><small>Selected operating scope · EUR million</small></div><button data-story-view="profitability">Explore</button></div>${divisions.map(d=>`<button class="story-contribution" data-story-division="${esc(d.division)}"><span>${esc(d.division)}</span><i><b style="width:${Math.abs(d.ebit)/dmax*100}%"></b></i><strong>${money(d.ebit)}</strong></button>`).join('')}</section>`;
  }
  function executiveNarrative(data,state,rv,ev){
    const entity=state.entity||'all',division=state.division||'all';
    const scopeLevel=entity!=='all'?(division!=='all'?'Entity Division':'Entity'):(division!=='all'?'Division':'Group');
    const rows=(data.performance_review||[]).filter(row=>row.review_month===data.meta.end_month&&row.scope_level===scopeLevel&&row.entity===(entity==='all'?'All':entity)&&row.division===(division==='all'?'All':division));
    const effects=['Price effect','Volume effect','Mix effect'].map(metric=>rows.find(row=>row.category==='Commercial Drivers'&&row.metric===metric&&row.comparison==='Prior year')).filter(Boolean);
    const signed=value=>`${value<0?'−':'+'}€${money(Math.abs(value))}m`;
    const driver=effects.length===3?effects.map(row=>`${row.metric.replace(' effect','')} ${signed(row.actual_value)}`).join(' · '):null;
    const driverFallback=rows.find(row=>row.action_required)||rows.find(row=>row.category==='Commercial Drivers')||rows.find(row=>row.category==='Monthly P&L vs Budget'&&row.metric==='EBIT');
    const driverText=driver||driverFallback?.headline||'No comparable published driver is available for this exact scope.';
    const driverSource=effects[0]||driverFallback;
    const groupOutlook=(data.performance_review||[]).find(row=>row.review_month===data.meta.end_month&&row.scope_level==='Group'&&row.category==='FY Outlook'&&row.metric==='FY EBIT outlook');
    const activeActions=(data.management_actions||[]).filter(action=>['Open','In Progress'].includes(action.status)&&action.scope_level===scopeLevel&&action.entity===(entity==='all'?'All':entity)&&action.division===(division==='all'?'All':division)).sort((a,b)=>a.priority.localeCompare(b.priority)||a.due_month.localeCompare(b.due_month));
    const action=activeActions[0];
    const scopeLabel=`${entity==='all'?'All entities':entity} · ${division==='all'?'All divisions':division}`;
    const result=`Revenue ${C().percent(rv.relative)} vs PY · EBIT ${C().percent(ev.relative)} vs PY`;
    const evidence=driverSource?`Review source · ${driverSource.source_dataset} · ${driverSource.source_key}`:'Source · performance_review';
    const actionText=action?`${action.priority} action · ${action.trigger_metric} · ${action.owner_role} · due ${action.due_month}`:'No active action is assigned to this exact scope.';
    return `<section class="story-narrative" aria-label="Executive narrative"><div class="story-narrative-result"><span>RESULT · ${esc(data.meta.end_month)} close</span><h2>${esc(result)}</h2><p>Selected scope · ${esc(scopeLabel)}</p></div><div class="story-narrative-step"><span>WHY IT MOVED · ${esc(scopeLabel)}</span><strong>${esc(driverText)}</strong><small>${esc(evidence)}</small><button data-story-view="performance-review">Open monthly review →</button></div><div class="story-narrative-step"><span>OUTLOOK &amp; RESPONSE · GROUP OUTLOOK</span><strong>${esc(groupOutlook?.headline||'Group full-year EBIT outlook is unavailable for this close.')}</strong><small>${esc(actionText)}</small><button data-story-view="action-execution">Open action register →</button></div></section>`;
  }
  function cashTree(data){
    const cf=(data.cash_flow||[]).at(-1)||{},wc=(data.working_capital||[]).at(-1)||{};
    return `<section class="tower-drivers"><div class="story-region-head"><div><h3>Free cash flow driver tree</h3><small>Current close · source-tied values</small></div><button data-story-focus="free-cash-flow">Explain</button></div><div class="driver-tree"><button data-story-focus="free-cash-flow"><span>Free cash flow</span><strong>€${money(cf.free_cash_flow)}m</strong></button><div><button data-story-view="cash-flow"><span>Operating cash flow</span><strong>€${money(cf.operating_cash_flow)}m</strong></button><b>+</b><button data-story-view="operations-capex"><span>Investing cash flow</span><strong>€${money(cf.investing_cash_flow)}m</strong></button></div><aside><span>Cash conversion watch</span><strong>NWC €${money(wc.net_working_capital)}m</strong></aside></div></section>`;
  }
  function inspectorTemplates(data,state,ac,py,cf,wc){
    const items={
      revenue:['Revenue',`€${money(ac?.revenue)}m`,M().variance(ac?.revenue,py?.revenue),'Sum of management P&L revenue for the selected operating scope.','management_detail','pnl','Revenue → entity → division'],
      ebit:['EBIT',`€${money(ac?.ebit)}m`,M().variance(ac?.ebit,py?.ebit),'Revenue less variable costs, fixed production costs, OPEX and depreciation.','management_detail','pnl','EBIT → division → entity'],
      'gross-margin':['Gross margin',pct(ac?.gross_profit/ac?.revenue),M().variance(ac?.gross_profit/ac?.revenue,py?.gross_profit/py?.revenue),'Gross profit divided by revenue for the selected operating scope.','management_detail','margin','Gross margin → gross profit → product'],
      'free-cash-flow':['Free cash flow',`€${money(cf?.free_cash_flow)}m`,M().variance(cf?.free_cash_flow,(data.cash_flow||[]).at(-13)?.free_cash_flow),'Operating cash flow + investing cash flow. Asset go-live transfers are non-cash.','cash_flow + cash_flow_detail','cash-flow','Free cash flow → legal entity → cash movement'],
      'net-working-capital':['Net working capital',`€${money(wc?.net_working_capital)}m`,M().variance(wc?.net_working_capital,(data.working_capital||[]).at(-13)?.net_working_capital,-1),'Net trade receivables plus net inventory less external trade payables.','working_capital + AR/AP/inventory schedules','working-capital','NWC → component → entity → counterparty / product']
    };
    return Object.entries(items).map(([key,[label,value,delta,formula,source,route,lineage]])=>{
      const group=['free-cash-flow','net-working-capital'].includes(key);
      const scope=group?'Consolidated group · all entities and divisions':`${state.entity==='all'?'All entities':state.entity} · ${state.division==='all'?'All divisions':state.division}`;
      const comparison=key==='gross-margin'?(delta.delta===null?'No comparable':`${delta.delta>=0?'+':''}${(delta.delta*100).toFixed(1)} pp vs PY`):`${C().percent(delta.relative)} vs PY`;
      return `<template data-story-detail="${key}"><div class="inspector-value"><span>${esc(label)}</span><strong>${esc(value)}</strong><small class="${tone(delta)}">${esc(comparison)}</small></div><dl><div><dt>Calculation</dt><dd>${esc(formula)}</dd></div><div><dt>Source</dt><dd>dashboard.json → ${esc(source)}</dd></div><div><dt>Scope</dt><dd>${esc(scope)}</dd></div><div><dt>Period</dt><dd>${esc(data.meta.end_month)} published close</dd></div></dl><div class="inspector-lineage"><span>Evidence path</span><p>${esc(lineage)}</p></div><div class="inspector-actions"><button data-story-view="${route}">Open report</button><button data-story-view="action-execution">Actions</button><button data-story-view="data-journey">Trace data</button></div></template>`;
    }).join('');
  }
  function executivePages(data,state,overview){
    const rows=M().aggregate(data.management_detail,state),ac=rows.find(r=>r.month===data.meta.end_month),py=rows.find(r=>r.month===M().priorMonth(data.meta.end_month));
    const cf=(data.cash_flow||[]).at(-1),wc=(data.working_capital||[]).at(-1),rv=M().variance(ac?.revenue,py?.revenue),ev=M().variance(ac?.ebit,py?.ebit);
    const narrative=executiveNarrative(data,state,rv,ev);
    const grossMargin=M().variance(ac?.gross_profit/ac?.revenue,py?.gross_profit/py?.revenue),marginNote=grossMargin.delta===null?'No comparable':`${grossMargin.delta>=0?'+':''}${(grossMargin.delta*100).toFixed(1)} pp vs PY`;
    const kpis=`<div class="story-kpis">${kpi('revenue','Revenue',`€${money(ac?.revenue)}m`,rv,'pnl')}${kpi('gross-margin','Gross margin',pct(ac?.gross_profit/ac?.revenue),grossMargin,'margin',marginNote)}${kpi('ebit','EBIT',`€${money(ac?.ebit)}m`,ev,'pnl')}${kpi('free-cash-flow','Free cash flow',`€${money(cf?.free_cash_flow)}m`,M().variance(cf?.free_cash_flow,(data.cash_flow||[]).at(-13)?.free_cash_flow),'cash-flow')}${kpi('net-working-capital','Net working capital',`€${money(wc?.net_working_capital)}m`,M().variance(wc?.net_working_capital,(data.working_capital||[]).at(-13)?.net_working_capital,-1),'working-capital')}</div>`;
    const trend=C().trend(M().comparisons(rows,'revenue',data.meta.end_month,12),'Revenue',760,255);
    const trendPanel=typeof innerWidth!=='undefined'&&innerWidth>1100&&innerWidth<=1700?executiveMiniTrend(rows,data.meta.end_month,true):`<section class="story-region story-trend"><div class="story-region-head"><div><h3>Revenue · Actual vs prior year</h3><small>EUR million · select a month for evidence</small></div><button data-story-view="pnl">View P&amp;L</button></div>${trend}</section>`;
    const overviewPage=`<article class="management-book control-tower">${narrative}${kpis}<div class="tower-layout"><div class="tower-canvas"><div class="tower-analytics">${trendPanel}${contribution(data,state)}${cashTree(data)}</div><div class="tower-bottom">${actionRail(data)}${storyLine(data)}</div></div><aside class="story-inspector" id="storyInspector" hidden><header><div><span>Selected KPI</span><h3>Evidence inspector</h3></div><button data-inspector-close aria-label="Close evidence inspector">×</button></header><div id="storyInspectorBody"></div></aside></div>${inspectorTemplates(data,state,ac,py,cf,wc)}</article>`;
    return [
      {title:'Overview',custom:true,policy:root.ReportContext.card('Revenue'),html:overviewPage},
      {title:'Drivers',custom:true,policy:root.ReportContext.card('Revenue'),html:`<div class="management-book story-board"><section class="story-region"><div class="story-region-head"><h3>Revenue to EBIT</h3><button data-story-view="pnl">Explain variance</button></div>${C().waterfall(ac,false)}</section>${contribution(data,state)}${desktopCanvas()?executiveMiniTrend(rows,data.meta.end_month):`<section class="story-region story-wide">${overview.match(/<section class="report-trend">[\s\S]*?<\/section>/)?.[0]||''}</section>`}</div>`},
      {title:'Outlook',custom:true,policy:root.ReportContext.group,html:outlook(data)},
      {title:'Actions',custom:true,policy:root.ReportContext.group,html:`<div class="management-book story-board">${actionRail(data)}<section class="story-region"><div class="story-region-head"><div><h3>Action portfolio</h3><small>Lifecycle of the current management response</small></div></div>${actionSummary(data)}</section>${storyLine(data)}</div>`}
    ];
  }
  function mount(){
    const inspector=document.getElementById('storyInspector'),body=document.getElementById('storyInspectorBody');if(!inspector||!body)return;
    const open=key=>{const template=document.querySelector(`template[data-story-detail="${key}"]`);if(!template)return;body.replaceChildren(template.content.cloneNode(true));inspector.hidden=false;document.querySelectorAll('[data-story-focus]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.storyFocus===key));body.querySelectorAll('[data-story-view]').forEach(button=>button.onclick=()=>{if(!button.dataset.storyView)return;state.view=button.dataset.storyView;reportState.page=0;render();});};
    document.querySelectorAll('[data-story-focus]').forEach(button=>button.onclick=()=>open(button.dataset.storyFocus));
    inspector.querySelector('[data-inspector-close]').onclick=()=>{inspector.hidden=true;document.querySelectorAll('[data-story-focus]').forEach(b=>b.setAttribute('aria-pressed','false'));};
    if(!window.matchMedia('(max-width: 900px)').matches)open('free-cash-flow');
  }
  function outlook(data){
    const base=(data.forecast||[]).filter(r=>r.scenario==='Base').slice(0,12),scenarios=(data.three_statement_forecast_summary||[]);
    return `<div class="management-book story-board"><section class="story-region story-wide executive-outlook-chart"><div class="story-region-head"><div><h3>Base revenue outlook</h3><small>FC · next 12 months · EUR million · signed zero baseline</small></div><button data-story-view="forecast">Open forecast</button></div>${desktopCanvas()?executiveMiniForecast(base):C().series(base,'revenue_forecast','month',data.meta.end_month,1000)}</section><section class="story-region"><div class="story-region-head"><h3>Scenario range</h3><button data-story-view="macro-sensitivities">Test sensitivities</button></div>${scenarios.map(s=>`<div class="story-scenario"><strong>${esc(s.scenario)}</strong><span>Revenue €${money(s.revenue_12m)}m</span><span>EBIT €${money(s.ebit_12m)}m</span><span>Cash €${money(s.ending_cash_12m)}m</span></div>`).join('')}</section>${storyLine(data)}</div>`;
  }
  function actionSummary(data){const s=(data.performance_review_summary||[])[0]||{};return `<div class="action-summary"><div><strong>${s.open_actions??0}</strong><span>Open</span></div><div><strong>${s.in_progress_actions??0}</strong><span>In progress</span></div><div><strong>${s.overdue_actions??0}</strong><span>Overdue</span></div><div><strong>${s.closed_actions??0}</strong><span>Closed</span></div></div>`;}
  function compose(pages){
    if(pages.length<=1)return pages;
    pages=pages.map(page=>page.fullScreen||page.contribution?page:{...page});
    const definitions=pages.find(page=>page.title==='Context & definitions');
    const definitionHost=pages.filter(page=>page!==definitions&&!page.fullScreen&&!page.contribution&&!page.html?.includes('class="report-indicators"')).at(-1);
    if(definitions&&definitionHost){
      definitionHost.html+=`<details class="report-definitions"><summary>Context & definitions</summary>${definitions.html}</details>`;
      pages=pages.filter(page=>page!==definitions);
    }
    // Indicator bands are supporting context, never a destination on their own.
    // Distribute them alongside evidence rather than pairing two KPI-only pages.
    const bands=pages.filter(p=>p.html?.includes('class="report-indicators"'));
    const evidence=pages.filter(p=>!bands.includes(p));
    const reviewOverview=typeof state!=='undefined'&&state.view==='performance-review'&&bands.length&&evidence.length;
    const statementOverview=typeof state!=='undefined'&&['pnl','working-capital','treasury','balance-sheet'].includes(state.view)&&bands.length&&evidence.length;
    const executionOverview=typeof state!=='undefined'&&state.view==='action-execution'&&bands.length&&evidence.length;
    if(bands.length&&evidence.length){
      const targets=evidence.filter(p=>!p.fullScreen&&!p.contribution);
      if(targets.length){
        if(!reviewOverview&&!statementOverview&&!executionOverview)bands.forEach((band,index)=>{
          const target=targets.find(candidate=>(candidate.policy?.key||'group')===(band.policy?.key||'group'))||targets[index%targets.length];
          target.html=`<section class="report-context-band" aria-label="${esc(band.title)}">${band.html}</section>${target.html}`;
          if((target.policy?.key||'group')!==(band.policy?.key||'group'))target.policy=root.ReportContext.group;
        });
        pages=evidence;
      }
    }
    const result=[];
    for(let i=0;i<pages.length;){
      const page=pages[i];
      if(page?.contribution||page?.fullScreen){result.push(page);i+=1;continue;}
      const next=pages[i+1];
      const pair=next&&!next.contribution&&!next.fullScreen?[page,next]:[page];
      const sameScope=pair.length===1||pair.every(p=>(p.policy?.key||'group')===(pair[0].policy?.key||'group'));
      result.push({title:pair.map(p=>p.title).join(' · '),policy:sameScope?pair[0].policy:root.ReportContext.group,custom:pair.some(p=>p.custom),html:`<div class="story-board ${pair.length===1?'story-single':''}">${pair.map(p=>`<section class="story-composite" data-source-section="${esc(p.title)}">${p.html}</section>`).join('')}</div>`});
      i+=pair.length;
    }
    if(reviewOverview&&result.length){
      result[0].html=`<div class="performance-review-overview"><section class="performance-review-indicators" aria-label="Review indicators">${bands.map(band=>band.html).join('')}</section>${result[0].html}</div>`;
    }
    if(statementOverview){
      const firstStory=result.find(page=>page.html?.startsWith('<div class="story-board'));
      if(firstStory){
        const host=document.createElement('div');
        host.innerHTML=bands.map(band=>band.html).join('');
        const cards=[...host.querySelectorAll('.kpi')];
        const priorities={pnl:['Revenue','Gross profit','EBIT','12M forecast EBIT'],'working-capital':['Gross receivables','Gross inventory','Trade payables','Provision-adjusted NWC'],treasury:['Group cash','Net cash','Liquidity headroom','Covenant status'],'balance-sheet':['Assets','Liabilities','Equity','Balance check']}[state.view];
        const headline=priorities.map(label=>cards.find(card=>card.querySelector('.kpi-label')?.textContent.trim()===label)).filter(Boolean);
        firstStory.html=`<div class="statement-story-overview statement-story-${esc(state.view)}"><section class="statement-story-indicators" aria-label="Key financial indicators">${headline.map(card=>card.outerHTML).join('')}<details class="statement-story-all"><summary>All ${cards.length} indicators</summary><div class="statement-story-all-grid">${cards.map(card=>card.outerHTML).join('')}</div></details></section>${firstStory.html}</div>`;
      }
    }
    if(executionOverview&&result.length){
      const host=document.createElement('div');
      host.innerHTML=bands.map(band=>band.html).join('');
      const cards=[...host.querySelectorAll('.kpi')];
      const priorities=['Approved plans','12M Revenue impact','12M EBIT impact','Current actual impact'];
      const headline=priorities.map(label=>cards.find(card=>card.querySelector('.kpi-label')?.textContent.trim()===label)).filter(Boolean);
      result[0].html=`<div class="action-story-overview"><section class="action-story-indicators" aria-label="Action execution indicators">${headline.map(card=>card.outerHTML).join('')}<details class="action-story-all"><summary>All ${cards.length} indicators</summary><div class="action-story-all-grid">${cards.map(card=>card.outerHTML).join('')}</div></details></section>${result[0].html}</div>`;
    }
    return result;
  }
  function mountResponsive(){
    mount();
    const tower=document.querySelector('.control-tower');
    if(!tower)return;
    const analytics=tower.querySelector('.tower-analytics');
    const compact=window.innerWidth<=1100;
    const regions=[analytics?.querySelector('.story-trend'),analytics?.querySelector('.tower-contribution'),analytics?.querySelector('.tower-drivers'),tower.querySelector('.story-timeline'),...(!compact?[tower.querySelector('.tower-actions')]:[])].filter(Boolean);
    if(analytics&&regions.length>1&&window.innerWidth<=1700){
      const switcher=document.createElement('nav');switcher.className='tower-region-switch';switcher.setAttribute('aria-label','Executive overview regions');
      const labels=['Performance trend','EBIT contribution','Cash drivers','Company story','Management priorities'];
      const selected=Math.min(executiveRegionIndex,regions.length-1);
      switcher.innerHTML=regions.map((region,index)=>`<button type="button" aria-pressed="${index===selected}" aria-controls="executive-region-${index}">${labels[index]}</button>`).join('');
      regions.forEach((region,index)=>{region.id=`executive-region-${index}`;region.hidden=index!==selected;});analytics.before(switcher);
      [...switcher.children].forEach((button,index)=>button.onclick=()=>{executiveRegionIndex=index;regions.forEach((region,i)=>region.hidden=i!==index);[...switcher.children].forEach((item,i)=>item.setAttribute('aria-pressed',String(i===index)));regions[index].querySelector('button,select,input,[tabindex]')?.focus({preventScroll:true});});
    }
    tower.addEventListener('click',event=>{
      if(!event.target.closest('[data-story-focus]')||!window.matchMedia('(max-width:1700px)').matches)return;
      const body=document.getElementById('storyInspectorBody');
      reportDialog('Calculation & supporting evidence',`<div class="sw-evidence-dialog">${body.innerHTML}</div>`);
      document.querySelectorAll('#reportDialogBody [data-story-view]').forEach(button=>button.onclick=()=>{
        document.getElementById('reportDialog').close();state.view=button.dataset.storyView;reportState.page=0;render();
      });
    });
  }
  root.ManagementBook={executivePages,compose,mount:mountResponsive};
})(globalThis);
