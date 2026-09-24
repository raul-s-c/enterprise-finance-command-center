/* Source-tied, first-screen map of the synthetic monthly finance close. */
(function(root){
  const stages=[
    {name:'Public macro drivers',input:'Official observations with deterministic fallback',output:'Month-level macro lineage',control:'macro_lineage_missing_rows',label:'Complete macro lineage',view:'macro-sensitivities',evidence:'Macro & sensitivities'},
    {name:'Business drivers',input:'Macro, product and capacity assumptions',output:'Demand, price, mix and operating capacity',control:'sensitivity_detail_summary_max_gap',label:'Driver sensitivity tie-out',view:'business-drivers',evidence:'Business drivers'},
    {name:'Operating transactions',input:'Orders, invoices and operating events',output:'Classified customer and supplier sources',control:'contract_ar_subledger_max_gap',label:'Customer subledger tie-out',view:'working-capital',evidence:'Working capital'},
    {name:'Double-entry ledger',input:'Classified events and chart-of-accounts rules',output:'Balanced journal and trial balance',control:'journal_balance_max_gap',label:'Journal debit / credit balance',view:'close-journey',evidence:'Close journey'},
    {name:'Legal entities',input:'Posted journal and period-end routines',output:'Entity financial positions',control:'legal_balance_sheet_max_gap',label:'Legal balance-sheet identity',view:'balance-sheet',evidence:'Balance sheet'},
    {name:'Consolidation',input:'Legal accounts and intercompany matches',output:'Eliminated group performance',control:'consolidation_revenue_max_gap',label:'Revenue consolidation tie-out',view:'intercompany',evidence:'Intercompany'},
    {name:'Financial statements',input:'Consolidated trial balance',output:'P&L, balance sheet and cash flow',control:'cash_flow_reconciliation_max_gap',label:'Cash-flow reconciliation',view:'cash-flow',evidence:'Cash flow'},
    {name:'Working-capital schedules',input:'AR, AP and inventory documents',output:'Reconciled closing schedules',control:'ar_subledger_max_gap',label:'Receivables subledger tie-out',view:'working-capital',evidence:'Working capital'},
    {name:'Rolling forecast',input:'Actuals, budget and scenario drivers',output:'Linked three-statement outlook',control:'forecast_lookahead_errors',label:'No forecast look-ahead',view:'forecast',evidence:'Plan & forecast'},
    {name:'CFO analytics',input:'Reconciled variances and source evidence',output:'Performance review and owned actions',control:'performance_review_source_max_gap',label:'Review-to-source tie-out',view:'performance-review',evidence:'Performance review'}
  ];
  const families=[
    ['Ledger & statements',/journal|trial|balance_sheet|cash_flow|debt|asset|pnl/],
    ['Subledgers & working capital',/ar_|ap_|inventory|contract|credit_loss|supplier|working_capital/],
    ['Consolidation & FX',/consolidat|intercompany|ic_|fx_|currency|translation/],
    ['Planning & governance',/forecast|budget|plan|action|review|macro|sensitivity|workforce/]
  ];
  let selected=0;
  const esc=value=>root.FinanceReport.escape(String(value??''));
  function controlGroups(validation){
    const result=families.map(([name])=>({name,count:0}));
    result.push({name:'Operations & other',count:0});
    for(const key of Object.keys(validation||{}).filter(key=>key!=='passed')){
      const index=families.findIndex(([,pattern])=>pattern.test(key));
      result[index<0?result.length-1:index].count++;
    }
    return result;
  }
  function stageDetail(data){
    const stage=stages[selected],value=data.validation?.[stage.control];
    return '<div class="dj-step-summary"><small>Selected stage · '+String(selected+1).padStart(2,'0')+' / 10</small><h3>'+esc(stage.name)+'</h3><p>'+esc(stage.input)+' → '+esc(stage.output)+'</p></div>'+
      '<div class="dj-step-fact"><small>Accounting output</small><strong>'+esc(stage.output)+'</strong></div>'+
      '<div class="dj-step-fact"><small>Release control</small><strong>'+esc(stage.label)+'</strong><span>'+esc(value===undefined?'Not published':value)+' · '+esc(stage.control)+'</span></div>'+
      '<div class="dj-step-fact dj-step-evidence"><small>Supporting evidence</small><button data-dj-evidence="'+esc(stage.view)+'">Open '+esc(stage.evidence)+' <span aria-hidden="true">↗</span></button></div>';
  }
  function page(data){
    const validation=data.validation||{},groups=controlGroups(validation),count=groups.reduce((sum,group)=>sum+group.count,0);
    const source=data.sources||{},macro=Object.values(source.macro_drivers||{}),official=macro.reduce((sum,item)=>sum+(Number(item.official_rows)||0),0),fallback=macro.reduce((sum,item)=>sum+(Number(item.fallback_rows)||0),0);
    const cards=stages.map((stage,index)=>'<button class="dj-stage" data-dj-stage="'+index+'" aria-pressed="'+(selected===index)+'"><span class="dj-stage-number">'+String(index+1).padStart(2,'0')+'</span><strong>'+esc(stage.name)+'</strong><span class="dj-stage-check" aria-label="'+(validation.passed?'Release controls passed':'Release review required')+'"></span></button>').join('');
    const groupRows=groups.map(group=>'<div class="dj-control-row"><span>'+esc(group.name)+'</span><div aria-hidden="true"><i style="width:'+((group.count/Math.max(count,1))*100).toFixed(1)+'%"></i></div><strong>'+group.count+'</strong></div>').join('');
    const sources='<div class="dj-source-row"><strong>Macro observations</strong><span>'+official.toLocaleString('en-US')+' official · '+fallback+' fallback</span></div>'+
      '<div class="dj-source-row"><strong>FX reference rates</strong><span>'+Number(source.fx?.live_rows||0).toLocaleString('en-US')+' live rows · '+esc(source.fx?.fallback||'Fallback unavailable')+'</span></div>'+
      '<div class="dj-source-row"><strong>Operating drivers</strong><span>'+esc(source.economic_drivers?.current||'Source unavailable')+'</span></div>';
    return {title:'Close map',custom:true,policy:root.ReportContext.group,html:'<article class="dj-cockpit"><header class="dj-head"><div><h2>From source to CFO decision</h2><p>Ten connected stages · published '+esc(data.meta.end_month)+' close · select any stage to trace its evidence</p></div><button data-dj-action="controls">Explore all controls</button></header>'+
      '<nav class="dj-map" aria-label="End-to-end finance pipeline">'+cards+'</nav>'+
      '<section class="dj-detail" aria-live="polite">'+stageDetail(data)+'</section>'+
      '<div class="dj-bottom"><section class="dj-panel"><header><div><h3>Release controls</h3><p>Share of published validation measures by family</p></div><strong class="'+(validation.passed?'dj-passed':'dj-review')+'">'+count+' measures · '+(validation.passed?'Passed':'Review required')+'</strong></header><div class="dj-control-rows">'+groupRows+'</div></section>'+
      '<section class="dj-panel"><header><div><h3>Source lineage</h3><p>Observed inputs and disclosed fallback</p></div><button data-dj-action="sources">Trace sources</button></header><div class="dj-source-rows">'+sources+'</div></section></div></article>'};
  }
  function mount(data){
    const host=document.querySelector('.dj-cockpit');
    if(!host)return;
    const detail=host.querySelector('.dj-detail');
    const bindEvidence=()=>{detail.querySelector('[data-dj-evidence]').onclick=event=>{state.view=event.currentTarget.dataset.djEvidence;reportState.page=0;render();};};
    bindEvidence();
    host.querySelectorAll('[data-dj-stage]').forEach(button=>button.onclick=()=>{
      selected=Number(button.dataset.djStage);
      host.querySelectorAll('[data-dj-stage]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
      detail.innerHTML=stageDetail(data);
      bindEvidence();
    });
    host.querySelector('[data-dj-action="controls"]').onclick=()=>{
      reportState.page=reportState.pages.findIndex(item=>item.title.includes('Release controls'));
      if(reportState.page<0)reportState.page=0;
      render();
    };
    host.querySelector('[data-dj-action="sources"]').onclick=()=>{state.view='macro-sensitivities';reportState.page=0;render();};
  }
  root.DataJourneyCockpit={page,mount,controlGroups,stages};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.DataJourneyCockpit;
})(globalThis);
