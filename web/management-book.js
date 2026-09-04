/* Multi-visual management-book composition over published finance data. */
(function(root){
  const M=()=>root.FinanceReport,C=()=>root.ReportCharts;
  const esc=v=>M().escape(String(v??'')),money=v=>C().money(v),pct=v=>M().finite(v)?`${(v*100).toFixed(1)}%`:'—';
  function kpi(label,value,delta,route,note){return `<div class="story-kpi"><span>${esc(label)}</span><strong>${esc(value)}</strong><small class="${delta?.favorable===true?'favorable':delta?.favorable===false?'unfavorable':''}">${esc(note||(delta?.relative===null?'No comparable':`${C().percent(delta?.relative)} vs PY`))}</small><button data-story-view="${route}">Explore</button></div>`;}
  function actionRail(data){
    const active=(data.management_actions||[]).filter(a=>['Open','In Progress'].includes(a.status)).sort((a,b)=>a.priority.localeCompare(b.priority)||a.due_month.localeCompare(b.due_month)).slice(0,3);
    return `<aside class="story-actions"><div class="story-region-head"><h3>Management priorities</h3><button data-story-view="action-execution">View all</button></div>${active.map((a,i)=>`<button class="story-action" data-action-id="${esc(a.action_id)}"><b>${i+1}</b><span><strong>${esc(a.trigger_metric)}</strong><small>${esc(a.action)}</small><em>${esc(a.owner_role)} · due ${esc(a.due_month)}</em></span><i>${esc(a.priority)}</i></button>`).join('')}</aside>`;
  }
  function storyLine(data){
    const actual=(data.actual||[]).slice(-36),w=1000,h=100,vals=actual.map(r=>r.revenue),min=Math.min(...vals),max=Math.max(...vals),span=max-min||1;
    const points=actual.map((r,i)=>`${i/(actual.length-1)*w},${15+(max-r.revenue)/span*45}`).join(' ');
    const milestones=[];
    const cap=(data.capex||[]).find(r=>r.event==='GO_LIVE');if(cap)milestones.push([cap.month,cap.project_name,'Factory go-live']);
    const phase=(data.portfolio_events||[]).find(r=>r.event==='PHASE_OUT_APPROVED');if(phase)milestones.push([phase.month,phase.product,'Portfolio decision']);
    const act=(data.management_actions||[]).find(a=>['Open','In Progress'].includes(a.status));if(act)milestones.push([act.opened_month,act.trigger_metric,'Recovery action']);
    return `<section class="story-timeline"><div class="story-region-head"><div><h3>36-month company story</h3><small>Revenue trajectory · actual close history · source: management P&amp;L</small></div><button data-story-view="data-journey">Trace data</button></div><svg viewBox="0 0 ${w} 62" preserveAspectRatio="none" role="img" aria-label="36 month revenue history"><polyline points="${points}" fill="none" stroke="#25282c" stroke-width="2"/></svg><div class="story-milestones">${milestones.map(m=>`<span><b>${esc(m[0])}</b>${esc(m[2])} · ${esc(m[1])}</span>`).join('')}</div></section>`;
  }
  function executivePages(data,state,overview){
    const rows=M().aggregate(data.management_detail,state),ac=rows.find(r=>r.month===data.meta.end_month),py=rows.find(r=>r.month===M().priorMonth(data.meta.end_month));
    const cf=(data.cash_flow||[]).at(-1),wc=(data.working_capital||[]).at(-1),actions=actionRail(data);
    const headline=`${M().variance(ac?.revenue,py?.revenue).delta>=0?'Revenue growth continues':'Revenue softened'}; ${M().variance(ac?.ebit,py?.ebit).delta>=0?'profitability is holding':'profitability needs attention'} and cash conversion remains the next management focus`;
    const grossMargin=M().variance(ac?.gross_profit/ac?.revenue,py?.gross_profit/py?.revenue);
    const marginNote=grossMargin.delta===null?'No comparable':`${grossMargin.delta>=0?'+':''}${(grossMargin.delta*100).toFixed(1)} pp vs PY`;
    const kpis=`<div class="story-kpis">${kpi('Revenue',`€${money(ac?.revenue)}m`,M().variance(ac?.revenue,py?.revenue),'pnl')}${kpi('EBIT',`€${money(ac?.ebit)}m`,M().variance(ac?.ebit,py?.ebit),'pnl')}${kpi('Gross margin',pct(ac?.gross_profit/ac?.revenue),grossMargin,'margin',marginNote)}${kpi('Free cash flow',`€${money(cf?.free_cash_flow)}m`,M().variance(cf?.free_cash_flow,(data.cash_flow||[]).at(-13)?.free_cash_flow),'cash-flow')}${kpi('Net working capital',`€${money(wc?.net_working_capital)}m`,M().variance(wc?.net_working_capital,(data.working_capital||[]).at(-13)?.net_working_capital,-1),'working-capital')}</div>`;
    const trend=C().trend(M().comparisons(rows,'revenue',data.meta.end_month,12),'Revenue',760,300);
    const divisions=(data.division||[]).slice().sort((a,b)=>b.ebit-a.ebit),dmax=Math.max(...divisions.map(d=>Math.abs(d.ebit)),1);
    const contribution=`<section class="story-region"><div class="story-region-head"><div><h3>EBIT contribution by division</h3><small>Current close · EUR million · source: management P&amp;L</small></div><button data-story-view="profitability">Explore</button></div>${divisions.map(d=>`<button class="story-contribution" data-story-division="${esc(d.division)}"><span>${esc(d.division)}</span><i><b style="width:${Math.abs(d.ebit)/dmax*100}%"></b></i><strong>${money(d.ebit)}</strong></button>`).join('')}</section>`;
    const overviewPage=`<article class="management-book"><header class="story-head"><div><h2>${esc(headline)}</h2><p>${esc(state.entity==='all'?'Group':state.entity)} performance · selected operating scope; group cash and NWC remain consolidated</p></div><button data-story-view="performance-review">Open monthly review</button></header>${kpis}<div class="story-main"><section class="story-region story-trend"><div class="story-region-head"><div><h3>Revenue performance</h3><small>AC / PY · latest 12 months · select a month</small></div><button data-story-view="pnl">View P&amp;L</button></div>${trend}</section><div class="story-right">${contribution}${actions}</div></div>${storyLine(data)}</article>`;
    return [
      {title:'Overview',custom:true,policy:root.ReportContext.card('Revenue'),html:overviewPage},
      {title:'Drivers',custom:true,policy:root.ReportContext.card('Revenue'),html:`<div class="management-book story-board"><section class="story-region"><div class="story-region-head"><h3>Revenue to EBIT</h3><button data-story-view="pnl">Explain variance</button></div>${C().waterfall(ac,false)}</section>${contribution}<section class="story-region story-wide">${overview.match(/<section class="report-trend">[\s\S]*?<\/section>/)?.[0]||''}</section></div>`},
      {title:'Outlook',custom:true,policy:root.ReportContext.group,html:outlook(data)},
      {title:'Actions',custom:true,policy:root.ReportContext.group,html:`<div class="management-book story-board">${actions}<section class="story-region"><div class="story-region-head"><div><h3>Action portfolio</h3><small>Lifecycle of the current management response</small></div></div>${actionSummary(data)}</section>${storyLine(data)}</div>`}
    ];
  }
  function outlook(data){
    const base=(data.forecast||[]).filter(r=>r.scenario==='Base').slice(0,12),scenarios=(data.three_statement_forecast_summary||[]);
    return `<div class="management-book story-board"><section class="story-region story-wide"><div class="story-region-head"><div><h3>Base revenue outlook</h3><small>FC · next 12 months · EUR million</small></div><button data-story-view="forecast">Open forecast</button></div>${C().series(base,'revenue_forecast','month',data.meta.end_month,1000)}</section><section class="story-region"><div class="story-region-head"><h3>Scenario range</h3><button data-story-view="macro-sensitivities">Test sensitivities</button></div>${scenarios.map(s=>`<div class="story-scenario"><strong>${esc(s.scenario)}</strong><span>Revenue €${money(s.revenue_12m)}m</span><span>EBIT €${money(s.ebit_12m)}m</span><span>Cash €${money(s.ending_cash_12m)}m</span></div>`).join('')}</section>${storyLine(data)}</div>`;
  }
  function actionSummary(data){const s=(data.performance_review_summary||[])[0]||{};return `<div class="action-summary"><div><strong>${s.open_actions??0}</strong><span>Open</span></div><div><strong>${s.in_progress_actions??0}</strong><span>In progress</span></div><div><strong>${s.overdue_actions??0}</strong><span>Overdue</span></div><div><strong>${s.closed_actions??0}</strong><span>Closed</span></div></div>`;}
  function compose(pages){
    if(pages.length<=1)return pages;
    const result=[];
    for(let i=0;i<pages.length;i+=2){const pair=pages.slice(i,i+2),sameScope=pair.length===1||pair.every(p=>(p.policy?.key||'group')===(pair[0].policy?.key||'group'));result.push({title:pair.map(p=>p.title).join(' · '),policy:sameScope?pair[0].policy:root.ReportContext.group,custom:pair.some(p=>p.custom),html:`<div class="story-board ${pair.length===1?'story-single':''}">${pair.map(p=>`<section class="story-composite" data-source-section="${esc(p.title)}">${p.html}</section>`).join('')}</div>`});}
    return result;
  }
  root.ManagementBook={executivePages,compose};
})(globalThis);
