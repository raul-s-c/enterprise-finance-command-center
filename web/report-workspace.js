/* Paginated reporting workspace over the unchanged release renderers and datasets. */
const reportState={page:0,view:null,metric:'revenue',initialized:false,pages:[],section:null};
const RM=FinanceReport,RC=ReportCharts;
// Existing report modules share this renderer: no negative bars drawn above zero.
bars=function(rows,key,labelKey='month'){return RC.series(rows||[],key,labelKey,data?.meta?.end_month||'',window.innerWidth<700?Math.max(300,window.innerWidth-28):900);};
const reportGroups=[
  ['Overview',['executive','performance-review','action-execution']],
  ['Financials',['pnl','margin','working-capital','cash-flow','treasury','balance-sheet']],
  ['Planning',['forecast','macro-sensitivities']],
  ['Operations',['business-drivers','profitability','intercompany','operations-capex','fx']],
  ['Data',['data-journey']]
];
const reportIcon=(name='next')=>`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">${name==='prev'?'<path d="m12 4-6 6 6 6"/>':name==='next'?'<path d="m8 4 6 6-6 6"/>':name==='chart'?'<path d="M3 3v14h14M5 12l4-5 4 3 4-6"/>':'<circle cx="10" cy="10" r="7"/><path d="M8 7c0-3 6-2 4 1l-2 2v2M10 14v1"/>'}</svg>`;
function reportNavIcon(id){
  const paths={
    executive:'M3 3v14h14M5 12l4-5 4 3 4-6',
    'performance-review':'M5 3h10v14H5zM7 7h6M7 10h6M7 13h4',
    'action-execution':'m3 5 2 2 3-4M10 5h7m-14 8 2 2 3-4m2 2h7',
    pnl:'M3 17V9h3v8m2 0V3h3v14m2 0V6h3v11',
    margin:'M4 16 16 4M6 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6M14 11a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
    'working-capital':'M3 5h14v11H3zM3 8h14M12 12h3',
    'cash-flow':'M2 10h4l2-6 4 12 2-6h4',
    treasury:'m2 7 8-4 8 4H2m2 2v6m4-6v6m4-6v6m4-6v6M2 17h16',
    'balance-sheet':'M10 3v14M4 5h12M5 5l-3 7h6L5 5m10 0-3 7h6l-3-7M6 17h8',
    forecast:'M3 5h14v12H3zM3 8h14M6 3v4m8-4v4M6 11h2m3 0h3m-8 3h2m3 0h3',
    'macro-sensitivities':'M2 14 6 8l4 3 6-8M12 3h4v4',
    'business-drivers':'M3 14a7 7 0 1 1 14 0M10 11l4-5M6 14h8',
    profitability:'M9 3a7 7 0 1 0 8 8H9V3m3 0v5h5a7 7 0 0 0-5-5',
    intercompany:'M3 6h14m-4-3 4 3-4 3M17 14H3m4-3-4 3 4 3',
    'operations-capex':'M3 17V8l5 3V7l5 3V3h3v14H3m3-3h1m3 0h1m3 0h1',
    fx:'M3 6h12m-3-3 3 3-3 3M17 14H5m3-3-3 3 3 3',
    'data-journey':'M3 5c0-4 14-4 14 0s-14 4-14 0v10c0 4 14 4 14 0V5M3 10c0 4 14 4 14 0'
  };
  return `<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round"><path d="${paths[id]||paths.executive}"/></svg>`;
}

function reportScope(){return `${state.entity==='all'?'All entities':state.entity} / ${state.division==='all'?'All divisions':state.division}`;}
function reportCurrent(){
  const rows=RM.aggregate(data.management_detail,state);
  return {rows,current:rows.find(r=>r.month===data.meta.end_month),prior:rows.find(r=>r.month===RM.priorMonth(data.meta.end_month))};
}
function reportMetric(label,value,note,delta){
  return `<div class="report-kpi"><div>${label}</div><strong>${value}</strong><small class="${delta?RC.tone(delta):''}">${note}</small></div>`;
}
function reportMoney(value){return RM.finite(value)?`€${RC.money(value)}m`:'—';}
function reportExecutive(){
  const {rows,current:l,prior:py}=reportCurrent(),v=RM.variance(l?.revenue,py?.revenue),ev=RM.variance(l?.ebit,py?.ebit);
  const cf=(data.cash_flow||[]).find(r=>r.month===data.meta.end_month),wc=(data.working_capital||[]).find(r=>r.month===data.meta.end_month);
  const gm=l&&l.revenue!==0&&RM.finite(l.gross_profit)?l.gross_profit/l.revenue:null;
  const headline=v.relative===null?'Explore revenue, profitability and cash conversion':`Revenue ${v.delta>=0?'increased':'decreased'} ${Math.abs(v.relative*100).toFixed(1)}% YoY`;
  const divisions=ReportContext.resolve(data,ReportContext.card('Revenue'),{...state,division:'all'}).options.division.filter(d=>state.division==='all'||state.division===d);
  const values=divisions.map(division=>{
    const series=RM.aggregate(data.management_detail,{...state,division});
    return {division,ac:series.find(r=>r.month===data.meta.end_month),py:series.find(r=>r.month===RM.priorMonth(data.meta.end_month))};
  });
  const max=Math.max(...values.map(r=>Math.abs(RM.variance(r.ac?.ebit,r.py?.ebit).delta||0)),1);
  return `<div class="executive-report"><h2 class="report-message">${headline}</h2><div class="report-kpis">
    ${reportMetric('Revenue',reportMoney(l?.revenue),`${RC.percent(v.relative)} YoY`,v)}
    ${reportMetric('EBIT',reportMoney(l?.ebit),`${RC.percent(ev.relative)} YoY`,ev)}
    ${reportMetric('Gross margin',RM.finite(gm)?`${(gm*100).toFixed(1)}%`:'—','Selected scope')}
    ${reportMetric('Group free cash flow',reportMoney(cf?.free_cash_flow),'Consolidated · not filtered')}
    ${reportMetric('Group net working capital',reportMoney(wc?.net_working_capital),'Consolidated · not filtered')}
  </div><div class="report-overview"><section class="report-trend"><div class="report-region-heading"><h3>${reportState.metric==='ebit'?'EBIT':'Revenue'} performance</h3><div class="metric-toggle" aria-label="Chart metric"><button data-metric="revenue" aria-pressed="${reportState.metric==='revenue'}">Revenue</button><button data-metric="ebit" aria-pressed="${reportState.metric==='ebit'}">EBIT</button></div></div><div class="chart-legend"><span class="actual-key">AC · Actual</span><span class="prior-key">PY · Prior year</span><span>EUR million · last ${window.innerWidth<700?6:12} months · select a month</span></div>${RC.trend(RM.comparisons(rows,reportState.metric,data.meta.end_month,window.innerWidth<700?6:12),reportState.metric==='ebit'?'EBIT':'Revenue',window.innerWidth<700?Math.max(300,window.innerWidth-28):800,window.innerWidth<700?320:Math.max(320,window.innerHeight-430))}</section>
  <section class="report-divisions"><h3>Division contribution</h3><p class="report-note">Click a division to filter · EUR million</p><table class="division-matrix"><thead><tr><th>Division</th><th>Revenue<br>AC</th><th>EBIT<br>AC</th><th>EBIT Δ PY</th></tr></thead><tbody>${values.map(r=>{const delta=RM.variance(r.ac?.ebit,r.py?.ebit);return `<tr><th><button data-division="${RM.escape(r.division)}">${RM.escape(r.division)}</button></th><td>${RC.money(r.ac?.revenue)}</td><td>${RC.money(r.ac?.ebit)}</td><td><span class="${RC.tone(delta)}">${RC.signed(delta.delta)}</span>${RC.varianceBar(delta,max)}</td></tr>`;}).join('')}</tbody></table><button class="report-link" data-open-pnl>Explore the P&L ${reportIcon()}</button></section></div></div>`;
}
function reportLegacyPages(view){
  const host=document.createElement('div');
  host.innerHTML=(renderers[view]||renderers.executive)();
  const pages=[];
  const indicators=[...host.querySelectorAll('.kpi')].filter(el=>!el.closest('.panel'));
  const chunks=window.innerWidth<700?4:6,groups=new Map();
  for(const el of indicators){
    const policy=ReportContext.card(el.querySelector('.kpi-label').textContent.trim());
    if(!groups.has(policy.key))groups.set(policy.key,{policy,items:[]});
    groups.get(policy.key).items.push(el);
  }
  for(const {policy,items} of groups.values())for(let i=0;i<items.length;i+=chunks)pages.push({title:`${policy.label}${i?` ${i/chunks+1}`:''}`,policy,html:`<div class="report-indicators">${items.slice(i,i+chunks).map(el=>el.outerHTML).join('')}</div>`});
  for(const el of host.querySelectorAll('.panel')){
    if(el.parentElement.closest('.panel'))continue;
    pages.push({title:el.querySelector('.panel-title')?.textContent||'Detail',html:el.outerHTML});
  }
  const notes=[...host.querySelectorAll('.section-note')].filter(el=>!el.closest('.panel'));
  if(notes.length)pages.push({title:'Context & definitions',html:`<article class="panel"><div class="panel-head"><div class="panel-title">Context & definitions</div></div><div class="report-text-pages">${notes.map(el=>`<div class="report-text-item">${el.outerHTML}</div>`).join('')}</div></article>`});
  if(!pages.length)pages.push({title:'Overview',html:host.innerHTML});
  return pages;
}
function reportPages(){
  const pages=reportLegacyPages(state.view),s=reportCurrent();
  if(state.view==='executive')pages.unshift({title:'Overview',html:reportExecutive(),custom:true});
  if(state.view==='pnl')pages.unshift(
    {title:'Performance',html:`<article class="financial-report"><h2 class="report-message">Understand the path from revenue to EBIT</h2>${RC.matrix(s.current,s.prior)}</article>`,custom:true},
    {title:'P&L bridge',html:`<article class="financial-report"><h2 class="report-message">Revenue to EBIT · EUR million</h2>${RC.waterfall(s.current,window.innerWidth<700)}</article>`,custom:true}
  );
  pages.push(...ContributionExplorer.pages(state.view));
  return pages;
}
function reportReadRoute(){
  const params=new URLSearchParams(location.hash.slice(1));
  if(views.some(v=>v[0]===params.get('view')))state.view=params.get('view');
  for(const [key,id] of [['entity','entityFilter'],['division','divisionFilter']]){
    const select=document.getElementById(id),value=params.get(key)||'all';
    state[key]=value==='all'||(data.management_detail||[]).some(r=>r[key]===value)?value:'all';
    select.value=state[key];
  }
  reportState.page=RM.pageIndex(params.get('page'));
  reportState.section=params.get('section');
  reportState.metric=params.get('metric')==='ebit'?'ebit':'revenue';
  reportState.view=state.view;
}
function reportNavigate(page){reportState.page=RM.pageIndex(page);render();}
function setupFilters(){
  for(const [key,id] of [['entity','entityFilter'],['division','divisionFilter']]){
    document.getElementById(id).onchange=event=>{
      reportState.section=reportState.pages[reportState.page]?.title;
      state[key]=event.target.value;render();
    };
  }
}
function reportFilterControls(page,resolved){
  const policy=page.policy||ReportContext.panel(state.view,page.title);
  for(const [key,id] of [['entity','entityFilter'],['division','divisionFilter']]){
    const select=document.getElementById(id),options=resolved.options[key];
    select.closest('label').hidden=!policy.dimensions.includes(key)||options.length===0;
    select.innerHTML=`<option value="all">All ${key==='entity'?'entities':'divisions'}</option>`+options.map(value=>`<option value="${RM.escape(value)}">${RM.escape(value)}</option>`).join('');
    select.value=state[key];
  }
  const reset=document.getElementById('reportReset');
  reset.hidden=policy.dimensions.length===0||resolved.empty;
  reset.disabled=policy.dimensions.every(key=>state[key]==='all');
  const scope=policy.dimensions.length?policy.dimensions.map(key=>`${key==='entity'?'Entity':'Division'}: ${state[key]==='all'?'All':state[key]}`).join(' · '):'Group / fixed report scope · no entity or division filter applies';
  document.getElementById('reportContext').innerHTML=`<span>${RM.escape(scope)}${resolved.adjusted.length?' · Selection adjusted':''}</span><span>${resolved.adjusted.length?`Selection broadened: ${RM.escape(resolved.adjusted.join(' and '))} had no records here.`:policy.dimensions.length?'Only available combinations are offered.':'Your operating selection is retained for other pages.'}</span>`;
  document.getElementById('reportContext').setAttribute('aria-live','polite');
}
function setupNav(){
  document.body.classList.add('report-mode');
  document.getElementById('nav').innerHTML=reportGroups.map(([group,ids])=>`<div class="nav-group"><div class="nav-group-title">${group}</div>${ids.map(id=>{const v=views.find(x=>x[0]===id);return v?`<button data-view="${id}">${reportNavIcon(id)}<span>${v[1]}</span></button>`:'';}).join('')}</div>`).join('');
  document.getElementById('nav').addEventListener('click',event=>{const button=event.target.closest('[data-view]');if(button){state.view=button.dataset.view;render();}});
  document.querySelector('.filters').insertAdjacentHTML('beforeend','<button id="reportReset" title="Reset entity and division filters">Reset</button><button id="reportHelp">Help</button>');
  document.querySelector('.topbar').insertAdjacentHTML('beforebegin',`<label class="mobile-module">Report<select id="reportModule">${views.map(v=>`<option value="${v[0]}">${v[1]}</option>`).join('')}</select></label>`);
  document.querySelector('.topbar').insertAdjacentHTML('afterend','<div class="report-subnav"><nav id="reportTabs" aria-label="Report subpages"></nav><label class="report-page-select">Subpage<select id="reportPageSelect"></select></label></div><div id="reportContext" class="report-context"></div>');
  document.querySelector('.main-shell').insertAdjacentHTML('beforeend',`<footer class="report-footer"><span id="reportStatus"></span><span class="synthetic-note">Synthetic enterprise · source-tied reporting</span><div class="report-page-controls"><button id="reportPrevious" aria-label="Previous subpage">${reportIcon('prev')}<span>Previous</span></button><span id="reportPageNumber" aria-live="polite"></span><button id="reportNext" aria-label="Next subpage"><span>Next</span>${reportIcon()}</button></div></footer>`);
  document.body.insertAdjacentHTML('beforeend','<dialog id="reportDialog" aria-labelledby="reportDialogTitle"><div class="dialog-heading"><h2 id="reportDialogTitle"></h2><button id="reportDialogClose">Close</button></div><div id="reportDialogBody"></div></dialog>');
  document.getElementById('reportDialogClose').onclick=()=>document.getElementById('reportDialog').close();
  document.getElementById('reportHelp').onclick=()=>reportDialog('How to read this report',`<div class="help-pages"><p><strong>Navigate.</strong> Choose a module on the left and a subpage above. Previous / Next visits every report block; the Subpage selector lists them all.</p><p><strong>Filter.</strong> Entity and division control supported operating detail. Group cash, working capital and other consolidated measures stay at group scope. Read each panel subtitle; no artificial allocation is made.</p><p><strong>Compare.</strong> AC is solid charcoal, PY gray. Green means favorable variance, red unfavorable. Negative amounts are not automatically unfavorable. Costs use lower-is-favorable logic. Missing comparisons show —, not zero.</p><p><strong>Explore.</strong> Select a month for values, click a division to filter, switch Revenue / EBIT, or open the P&L bridge. Tables have search, row pages and column pages; selecting a row opens its full detail.</p><p><strong>Trust.</strong> Data is from the synthetic company’s published close. FX remeasurement is analytical, not bank-matched. IBCS-inspired notation and custom visuals; not official or certified Zebra BI components.</p></div>`);
  document.getElementById('reportReset').onclick=()=>{state.entity=state.division='all';document.getElementById('entityFilter').value='all';document.getElementById('divisionFilter').value='all';render();};
  document.getElementById('reportModule').onchange=event=>{state.view=event.target.value;render();};
  document.getElementById('reportTabs').onclick=event=>{const button=event.target.closest('[data-page]');if(button)reportNavigate(Number(button.dataset.page));};
  document.getElementById('reportPageSelect').onchange=event=>reportNavigate(Number(event.target.value));
  document.getElementById('reportPrevious').onclick=()=>reportNavigate(reportState.page-1);
  document.getElementById('reportNext').onclick=()=>reportNavigate(reportState.page+1);
  window.addEventListener('popstate',()=>{if(data){reportReadRoute();render(true);}});
  window.addEventListener('hashchange',()=>{if(data){reportReadRoute();render(true);}});
  let resizeTimer;
  window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(data){reportState.section=reportState.pages[reportState.page]?.title;render(true);}},120);});
}
function reportDialog(title,body){
  document.getElementById('reportDialogTitle').textContent=title;
  document.getElementById('reportDialogBody').innerHTML=body;
  const dialog=document.getElementById('reportDialog');if(!dialog.open)dialog.showModal();
  const children=document.querySelector('#reportDialogBody .help-pages');
  if(children)reportListPager(children,1);
  const detail=document.querySelector('#reportDialogBody .row-detail');
  if(detail)reportListPager(detail,window.innerWidth<700?3:6);
}
function render(restoring=false){
  if(!data)return;
  const focused=document.activeElement;
  const focusId=focused?.id;
  const focusKey=['page','metric','division'].find(key=>focused?.dataset?.[key]!==undefined);
  const focusValue=focusKey?focused.dataset[focusKey]:null;
  if(!reportState.initialized){reportReadRoute();reportState.initialized=true;restoring=true;}
  if(reportState.view!==state.view){reportState.page=0;reportState.view=state.view;}
  const config=views.find(v=>v[0]===state.view)||views[0];let pages=reportPages();
  if(reportState.section){const index=pages.findIndex(p=>p.title===reportState.section);if(index>=0)reportState.page=index;reportState.section=null;}
  reportState.page=Math.max(0,Math.min(pages.length-1,reportState.page));
  const currentPage=pages[reportState.page],policy=currentPage.policy||ReportContext.panel(state.view,currentPage.title);
  const resolved=ReportContext.resolve(data,policy,state);
  if(resolved.adjusted.length){
    Object.assign(state,resolved.scope);pages=reportPages();
    reportState.page=Math.max(0,pages.findIndex(page=>page.title===currentPage.title));
  }
  reportState.pages=pages;
  document.getElementById('viewTitle').textContent=config[1];
  document.getElementById('viewSubtitle').textContent=`${data.meta.end_month} close · ${state.view==='executive'||state.view==='pnl'?'EUR million · AC / PY':'Source units shown in each report'}`;
  document.querySelectorAll('#nav [data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===state.view);b.setAttribute('aria-current',b.dataset.view===state.view?'page':'false');});
  document.getElementById('reportModule').value=state.view;
  const start=Math.max(0,Math.min(reportState.page-1,pages.length-4));
  document.getElementById('reportTabs').innerHTML=pages.slice(start,start+4).map((p,i)=>`<button data-page="${start+i}" aria-current="${start+i===reportState.page?'page':'false'}">${RM.escape(p.title)}</button>`).join('');
  document.getElementById('reportPageSelect').innerHTML=pages.map((p,i)=>`<option value="${i}" ${i===reportState.page?'selected':''}>${i+1}. ${RM.escape(p.title)}</option>`).join('');
  reportFilterControls(pages[reportState.page],resolved);
  document.getElementById('content').innerHTML=pages[reportState.page].html;
  ContributionExplorer.mount(data);
  document.getElementById('reportStatus').textContent=`${data.meta.end_month} · ${data.validation?.passed?'Controls passed':'CONTROLS FAILED'}`;
  document.getElementById('reportStatus').className=data.validation?.passed?'control-pass':'control-fail';
  document.getElementById('reportPageNumber').textContent=`${reportState.page+1} / ${pages.length}`;
  document.getElementById('reportPrevious').disabled=reportState.page===0;
  document.getElementById('reportNext').disabled=reportState.page===pages.length-1;
  const hash=new URLSearchParams({view:state.view,page:reportState.page,section:pages[reportState.page].title,entity:state.entity,division:state.division,metric:reportState.metric});
  if(location.hash!==`#${hash}`)history[restoring?'replaceState':'pushState'](null,'',`#${hash}`);
  document.querySelectorAll('[data-metric]').forEach(b=>b.onclick=()=>{reportState.metric=b.dataset.metric;render();});
  document.querySelectorAll('[data-division]').forEach(b=>b.onclick=()=>{state.division=b.dataset.division;document.getElementById('divisionFilter').value=state.division;render();});
  document.querySelectorAll('[data-open-pnl]').forEach(b=>b.onclick=()=>{state.view='pnl';render();});
  document.querySelectorAll('[data-month]').forEach(point=>{
    const show=()=>{const s=reportCurrent(),ac=s.rows.find(r=>r.month===point.dataset.month),py=s.rows.find(r=>r.month===RM.priorMonth(point.dataset.month));reportDialog(`${point.dataset.month} · ${reportScope()}`,`<div class="month-detail">${['revenue','gross_profit','ebit'].map(key=>{const v=RM.variance(ac?.[key],py?.[key]);return `<p><strong>${key.replaceAll('_',' ')}</strong><br>AC ${RC.money(ac?.[key])} · PY ${RC.money(py?.[key])} · Δ ${RC.signed(v.delta)} EUR m · ${RC.percent(v.relative)}</p>`;}).join('')}</div>`);};
    point.onclick=show;point.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}};
  });
  reportKpiHelp();
  for(const empty of document.querySelectorAll('#content .empty')){
    empty.innerHTML=`<strong>${pages[reportState.page].title==='Overdue and escalated actions'?'No overdue actions in this close':'No records in this published report'}</strong><p>This is not a loading error. The published snapshot contains no matching detail; financial zeros remain visible elsewhere.</p><button data-return-overview>Return to Executive</button>`;
    empty.querySelector('button').onclick=()=>{state.view='executive';render();};
  }
  if(focusKey){
    const replacement=[...document.querySelectorAll(`[data-${focusKey}]`)].find(el=>el.dataset[focusKey]===focusValue);
    (replacement||document.getElementById('reportPageSelect')).focus({preventScroll:true});
  }else if(focusId && (document.getElementById(focusId)?.disabled||document.getElementById(focusId)?.closest('[hidden]'))){
    document.getElementById('reportPageSelect').focus({preventScroll:true});
  }
  // Measurements force layout here, so every render returns with usable pagers and sorting.
  reportEnhancePage();
}
function reportKpiHelp(){
  for(const card of document.querySelectorAll('#content .kpi,#content .report-kpi')){
    const labelNode=card.querySelector('.kpi-label')||card.firstElementChild;
    const label=labelNode.textContent.trim(),definition=KpiDefinitions.get(label);
    const button=document.createElement('button');
    button.type='button';button.className='kpi-info';button.textContent='i';
    button.setAttribute('aria-label',`How ${label} is calculated`);
    button.setAttribute('aria-haspopup','dialog');
    button.title=`How ${label} is calculated`;
    button.dataset.kpi=label;
    button.onclick=()=>{
      const value=card.querySelector('.kpi-value,strong')?.textContent.trim()||'—';
      const fields=definition?[
        ['Calculation',definition.formula],
        ['Scope',`${definition.scope} Current selection: ${reportScope()}.`],
        ['Period',`${definition.period} Published close: ${data.meta.end_month}.`],
        ['Source',`dashboard.json → ${definition.source}`],
        ['Display',`Shown value: ${value}. Values are rounded for display (m/M = million). These labels do not change source calculations or controls. Some legacy cards display 0 for missing source values or zero denominators; a displayed zero alone does not establish data availability.`],
      ]:[['Definition unavailable','This indicator has no reviewed definition yet. Do not infer its calculation from its label.']];
      reportDialog(`${label} · calculation`,`<dl class="kpi-definition">${fields.map(([key,text])=>`<div><dt>${RM.escape(key)}</dt><dd>${RM.escape(text)}</dd></div>`).join('')}</dl>`);
      reportListPager(document.querySelector('.kpi-definition'),1);
    };
    labelNode.classList.add('kpi-label-with-help');labelNode.append(button);
  }
}
function reportListPager(container,size){
  const items=[...container.children];if(items.length<=size)return;
  let index=0;const controls=document.createElement('div');controls.className='table-pagination';
  container.after(controls);
  const update=()=>{const focused=reportPagerFocus(controls);const p=RM.page(items,index,size);index=p.index;items.forEach((el,i)=>el.hidden=i<index*size||i>=(index+1)*size);controls.innerHTML=`<button data-prev ${index===0?'disabled':''}>Previous items</button><span aria-live="polite">${index+1} / ${p.count}</span><button data-next ${index===p.count-1?'disabled':''}>Next items</button>`;controls.querySelector('[data-prev]').onclick=()=>{index--;update();};controls.querySelector('[data-next]').onclick=()=>{index++;update();};reportRestorePagerFocus(controls,focused);};update();
}
function reportPagerFocus(container){
  const active=document.activeElement;
  return container.contains(active)?['data-prev','data-next','data-col-prev','data-col-next'].find(key=>active.hasAttribute(key)):null;
}
function reportRestorePagerFocus(container,key){
  if(key)(container.querySelector(`[${key}]:not(:disabled)`)||container.querySelector('button:not(:disabled)'))?.focus({preventScroll:true});
}
function reportEnhancePage(){
  const content=document.getElementById('content');
  for(const wrap of content.querySelectorAll('.table-wrap'))reportTable(wrap);
  for(const list of content.querySelectorAll('.commentary,.review-list,.status-grid,.report-text-pages,.flow')){
    const available=content.getBoundingClientRect().bottom-list.getBoundingClientRect().top-65;
    reportListPager(list,Math.max(1,Math.floor(available/(list.matches('.status-grid')?82:list.matches('.review-list')?150:110))));
  }
}
function reportTable(wrap){
  if(wrap.dataset.paged)return;wrap.dataset.paged='true';
  const table=wrap.querySelector('table'),rows=[...table.tBodies[0].rows],headers=[...table.tHead.rows[0].cells];
  let pageIndex=0,columnIndex=0,query='',sortColumn=-1,sortDirection=1;
  const toolbar=document.createElement('div');toolbar.className='table-toolbar';
  toolbar.innerHTML='<label>Search rows <input type="search" placeholder="Find in this report"></label><span>Click a row for full detail</span>';
  wrap.before(toolbar);
  const footer=document.createElement('div');footer.className='table-pagination';wrap.after(footer);
  const height=document.getElementById('content').getBoundingClientRect().bottom-wrap.getBoundingClientRect().top-75;
  const size=Math.max(1,Math.floor((height-38)/36));
  const columns=Math.max(2,Math.floor(wrap.clientWidth/140)),columnCount=Math.max(1,Math.ceil((headers.length-1)/(columns-1)));
  const update=()=>{
    const focused=reportPagerFocus(footer);
    const selected=rows.filter(r=>r.textContent.toLowerCase().includes(query)),p=RM.page(selected,pageIndex,size);pageIndex=p.index;
    rows.forEach(r=>r.hidden=!p.items.includes(r));
    for(const row of [table.tHead.rows[0],...rows])for(let i=0;i<row.cells.length;i++)row.cells[i].hidden=i!==0&&(i<1+columnIndex*(columns-1)||i>=1+(columnIndex+1)*(columns-1));
    footer.innerHTML=`<span>${selected.length?`${pageIndex*size+1}–${Math.min((pageIndex+1)*size,selected.length)}`:'0'} of ${selected.length} rows</span><div><button data-prev ${pageIndex===0?'disabled':''} aria-label="Previous rows">${reportIcon('prev')}</button><span>${pageIndex+1} / ${p.count}</span><button data-next ${pageIndex===p.count-1?'disabled':''} aria-label="Next rows">${reportIcon()}</button></div>${columnCount>1?`<div><button data-col-prev ${columnIndex===0?'disabled':''} aria-label="Previous columns">${reportIcon('prev')}</button><span>Columns ${columnIndex+1} / ${columnCount}</span><button data-col-next ${columnIndex===columnCount-1?'disabled':''} aria-label="Next columns">${reportIcon()}</button></div>`:''}`;
    footer.querySelector('[data-prev]').onclick=()=>{pageIndex--;update();};footer.querySelector('[data-next]').onclick=()=>{pageIndex++;update();};
    if(columnCount>1){footer.querySelector('[data-col-prev]').onclick=()=>{columnIndex--;update();};footer.querySelector('[data-col-next]').onclick=()=>{columnIndex++;update();};}
    reportRestorePagerFocus(footer,focused);
  };
  toolbar.querySelector('input').oninput=event=>{query=event.target.value.toLowerCase();pageIndex=0;update();};
  headers.forEach((header,index)=>{
    const label=header.textContent,button=document.createElement('button');
    button.type='button';button.className='column-sort';button.textContent=label;
    button.setAttribute('aria-label',`Sort by ${label}`);header.replaceChildren(button);
    header.setAttribute('aria-sort','none');
    button.onclick=()=>{
      sortDirection=sortColumn===index?-sortDirection:1;sortColumn=index;pageIndex=0;
      rows.sort((a,b)=>RM.compareDisplay(a.cells[index]?.textContent,b.cells[index]?.textContent,header.classList.contains('num'))*sortDirection);
      table.tBodies[0].replaceChildren(...rows);
      headers.forEach((h,i)=>h.setAttribute('aria-sort',i===index?(sortDirection===1?'ascending':'descending'):'none'));
      update();
    };
  });
  for(const row of rows){
    row.tabIndex=0;
    const show=()=>{
      const selection={entity:'all',division:'all'};let hasScope=false;
      headers.forEach((header,i)=>{const key=header.textContent.trim().toLowerCase();if(key==='entity'||key==='division'){selection[key]=row.cells[i]?.textContent.trim();hasScope=true;}});
      const resolved=ReportContext.resolve(data,ReportContext.card('Revenue'),selection);
      const canExplore=hasScope&&!resolved.empty&&!resolved.adjusted.length;
      reportDialog('Row detail',`<dl class="row-detail">${headers.map((h,i)=>`<div><dt>${RM.escape(h.textContent)}</dt><dd>${RM.escape(row.cells[i]?.textContent)}</dd></div>`).join('')}</dl>${canExplore?'<button id="reportExploreScope">Explore this scope</button>':''}`);
      if(canExplore)document.getElementById('reportExploreScope').onclick=()=>{document.getElementById('reportDialog').close();Object.assign(state,selection,{view:'executive'});render();};
    };
    row.setAttribute('aria-label',`Open row detail: ${row.cells[0]?.textContent||'record'}`);
    row.onclick=show;row.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}};
    [...row.cells].forEach(cell=>cell.title=cell.textContent);
  }
  update();
}
