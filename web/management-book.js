/* Enterprise management book: one-screen narrative, evidence and action. */
(function(root){
  const M=()=>root.FinanceReport,C=()=>root.ReportCharts;
  const esc=v=>M().escape(String(v??'')),money=v=>C().money(v),pct=v=>M().finite(v)?`${(v*100).toFixed(1)}%`:'—';
  const tone=v=>v?.favorable===true?'favorable':v?.favorable===false?'unfavorable':'neutral';
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
  function contribution(data){
    const divisions=(data.division||[]).slice().sort((a,b)=>b.ebit-a.ebit),dmax=Math.max(...divisions.map(d=>Math.abs(d.ebit)),1);
    return `<section class="tower-contribution"><div class="story-region-head"><div><h3>EBIT contribution by division</h3><small>Current close · EUR million</small></div><button data-story-view="profitability">Explore</button></div>${divisions.map(d=>`<button class="story-contribution" data-story-division="${esc(d.division)}"><span>${esc(d.division)}</span><i><b style="width:${Math.abs(d.ebit)/dmax*100}%"></b></i><strong>${money(d.ebit)}</strong></button>`).join('')}</section>`;
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
    return Object.entries(items).map(([key,[label,value,delta,formula,source,route,lineage]])=>`<template data-story-detail="${key}"><div class="inspector-value"><span>${esc(label)}</span><strong>${esc(value)}</strong><small class="${tone(delta)}">${esc(C().percent(delta?.relative))} vs PY</small></div><dl><div><dt>Calculation</dt><dd>${esc(formula)}</dd></div><div><dt>Source</dt><dd>dashboard.json → ${esc(source)}</dd></div><div><dt>Scope</dt><dd>${esc(state.entity==='all'?'All entities':state.entity)} · ${esc(state.division==='all'?'All divisions':state.division)}</dd></div><div><dt>Period</dt><dd>${esc(data.meta.end_month)} published close</dd></div></dl><div class="inspector-lineage"><span>Lineage · click to explore</span>${lineage.split(' → ').map((step,i)=>`<button data-story-view="${i===0?route:''}"><b>${i+1}</b>${esc(step)}<i>›</i></button>`).join('')}</div><div class="inspector-actions"><button data-story-view="${route}">Explain</button><button data-story-view="action-execution">Contribute</button><button data-story-view="data-journey">Trace</button></div></template>`).join('');
  }
  function executivePages(data,state,overview){
    const rows=M().aggregate(data.management_detail,state),ac=rows.find(r=>r.month===data.meta.end_month),py=rows.find(r=>r.month===M().priorMonth(data.meta.end_month));
    const cf=(data.cash_flow||[]).at(-1),wc=(data.working_capital||[]).at(-1),rv=M().variance(ac?.revenue,py?.revenue),ev=M().variance(ac?.ebit,py?.ebit);
    const headline=`${rv.delta>=0?'Strong revenue growth':'Revenue softened'} and ${ev.delta>=0?'EBIT resilience':'profitability pressure'} in ${data.meta.end_month}; cash conversion remains the next management focus`;
    const grossMargin=M().variance(ac?.gross_profit/ac?.revenue,py?.gross_profit/py?.revenue),marginNote=grossMargin.delta===null?'No comparable':`${grossMargin.delta>=0?'+':''}${(grossMargin.delta*100).toFixed(1)} pp vs PY`;
    const kpis=`<div class="story-kpis">${kpi('revenue','Revenue',`€${money(ac?.revenue)}m`,rv,'pnl')}${kpi('gross-margin','Gross margin',pct(ac?.gross_profit/ac?.revenue),grossMargin,'margin',marginNote)}${kpi('ebit','EBIT',`€${money(ac?.ebit)}m`,ev,'pnl')}${kpi('free-cash-flow','Free cash flow',`€${money(cf?.free_cash_flow)}m`,M().variance(cf?.free_cash_flow,(data.cash_flow||[]).at(-13)?.free_cash_flow),'cash-flow')}${kpi('net-working-capital','Net working capital',`€${money(wc?.net_working_capital)}m`,M().variance(wc?.net_working_capital,(data.working_capital||[]).at(-13)?.net_working_capital,-1),'working-capital')}</div>`;
    const trend=C().trend(M().comparisons(rows,'revenue',data.meta.end_month,12),'Revenue',760,255);
    const overviewPage=`<article class="management-book control-tower"><header class="story-head"><div><h2>${esc(headline)}</h2><p>Revenue ${C().percent(rv.relative)} YoY · EBIT ${C().percent(ev.relative)} YoY · consolidated cash and working capital</p></div><button data-story-view="performance-review">Open monthly review</button></header>${kpis}<div class="tower-layout"><div class="tower-canvas"><div class="tower-analytics"><section class="story-region story-trend"><div class="story-region-head"><div><h3>Revenue · Actual vs prior year</h3><small>EUR million · select a month for evidence</small></div><button data-story-view="pnl">View P&amp;L</button></div>${trend}</section>${contribution(data)}${cashTree(data)}</div><div class="tower-bottom">${actionRail(data)}${storyLine(data)}</div></div><aside class="story-inspector" id="storyInspector" hidden><header><div><span>Selected KPI</span><h3>Evidence inspector</h3></div><button data-inspector-close aria-label="Close evidence inspector">×</button></header><div id="storyInspectorBody"></div></aside></div>${inspectorTemplates(data,state,ac,py,cf,wc)}</article>`;
    return [
      {title:'Overview',custom:true,policy:root.ReportContext.card('Revenue'),html:overviewPage},
      {title:'Drivers',custom:true,policy:root.ReportContext.card('Revenue'),html:`<div class="management-book story-board"><section class="story-region"><div class="story-region-head"><h3>Revenue to EBIT</h3><button data-story-view="pnl">Explain variance</button></div>${C().waterfall(ac,false)}</section>${contribution(data)}<section class="story-region story-wide">${overview.match(/<section class="report-trend">[\s\S]*?<\/section>/)?.[0]||''}</section></div>`},
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
    return `<div class="management-book story-board"><section class="story-region story-wide"><div class="story-region-head"><div><h3>Base revenue outlook</h3><small>FC · next 12 months · EUR million</small></div><button data-story-view="forecast">Open forecast</button></div>${C().series(base,'revenue_forecast','month',data.meta.end_month,1000)}</section><section class="story-region"><div class="story-region-head"><h3>Scenario range</h3><button data-story-view="macro-sensitivities">Test sensitivities</button></div>${scenarios.map(s=>`<div class="story-scenario"><strong>${esc(s.scenario)}</strong><span>Revenue €${money(s.revenue_12m)}m</span><span>EBIT €${money(s.ebit_12m)}m</span><span>Cash €${money(s.ending_cash_12m)}m</span></div>`).join('')}</section>${storyLine(data)}</div>`;
  }
  function actionSummary(data){const s=(data.performance_review_summary||[])[0]||{};return `<div class="action-summary"><div><strong>${s.open_actions??0}</strong><span>Open</span></div><div><strong>${s.in_progress_actions??0}</strong><span>In progress</span></div><div><strong>${s.overdue_actions??0}</strong><span>Overdue</span></div><div><strong>${s.closed_actions??0}</strong><span>Closed</span></div></div>`;}
  function compose(pages){
    if(pages.length<=1)return pages;
    const result=[];
    for(let i=0;i<pages.length;){
      const page=pages[i];
      if(page?.contribution||page?.fullScreen){result.push(page);i+=1;continue;}
      const next=pages[i+1];
      const pair=next&&!next.contribution?[page,next]:[page];
      const sameScope=pair.length===1||pair.every(p=>(p.policy?.key||'group')===(pair[0].policy?.key||'group'));
      result.push({title:pair.map(p=>p.title).join(' · '),policy:sameScope?pair[0].policy:root.ReportContext.group,custom:pair.some(p=>p.custom),html:`<div class="story-board ${pair.length===1?'story-single':''}">${pair.map(p=>`<section class="story-composite" data-source-section="${esc(p.title)}">${p.html}</section>`).join('')}</div>`});
      i+=pair.length;
    }
    return result;
  }
  root.ManagementBook={executivePages,compose,mount};
})(globalThis);
