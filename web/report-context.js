/* Data-backed UI domains. Zero measures are valid; absent records are not choices. */
(function(root){
  const group={key:'group',label:'Group indicators',datasets:[],dimensions:[]};
  const domain=(key,label,datasets,dimensions=['entity','division'],extra={})=>({key,label,datasets,dimensions,...extra});
  const operating=domain('operating','Operating indicators',['management_detail'],undefined,{activity:true});
  const software=domain('software','Software indicators',['software_entity_summary'],['entity']);
  const events=domain('events','Events indicators',['events_backlog_detail'],['entity']);
  const factory=domain('factory','Factory indicators',['hardware_factory_economics'],['entity'],{entityField:'factory'});
  const spare=domain('spare','Aftermarket indicators',['spare_parts_economics'],['entity']);
  const workforce=domain('workforce','Workforce indicators',['workforce_detail']);
  const contracts=domain('contracts','Customer funding indicators',['contract_entity_summary']);
  const review=domain('review','Review indicators',['performance_review'],undefined,{levels:true});
  const action=domain('actions','Action indicators',['management_actions'],undefined,{levels:true});
  const fx=domain('fx','Constant-currency indicators',['constant_currency']);
  const translation=domain('translation','Translation indicators',['fx_translation'],['entity']);
  const transactions=domain('transactions','Transaction FX indicators',['transaction_fx_close_documents']);
  const plan=domain('plan','Plan indicators',['fy_plan_bridge']);
  const workforcePlan=domain('workforce-plan','Workforce plan indicators',['workforce_forecast']);
  const actionPlan=domain('action-plan','Execution indicators',['management_action_plans'],undefined,{levels:true,allLevels:true});
  const actionBridge=domain('action-bridge','Action forecast indicators',['management_action_forecast_bridge']);
  const panels=Object.create(null);
  function register(policy,titles){for(const title of titles)panels[title]=policy;}
  register(operating,['Overview','Performance','P&L bridge','Revenue trend','Division performance','Monthly EBIT','Current month P&L','Entity and division detail','Margin hierarchy']);
  register(plan,['YTD performance','FY outlook evolution','Division plan bridge','Budget monthly phasing','Budget assumptions']);
  register(software,['ARR trend','ARR movement','Largest recurring positions']);
  register(events,['Backlog by family']);
  register(factory,['Factory absorption accounting']);
  register(spare,['Installed base by entity','Aftermarket trend']);
  register(workforce,['Workforce by function']);
  register(workforcePlan,['Base workforce plan']);
  register(contracts,['Prepayment funding by business']);
  register(review,['CFO performance narrative','Review coverage','Driver scorecard']);
  register(action,['Management action register','Persistent action register','Action lifecycle']);
  register(domain('history','Action history',['management_action_history'],undefined,{levels:true}),['Lifecycle trend']);
  register(domain('overdue','Overdue actions',['management_actions'],undefined,{levels:true,overdue:true}),['Overdue and escalated actions']);
  register(actionPlan,['Execution portfolio']);
  register(actionBridge,['Base forecast action bridge']);
  register(domain('benefits','Action benefits',['management_action_benefits'],undefined,{levels:true,allLevels:true}),['Directional benefit tracking']);
  register(domain('actual-impact','Actual action impact',['management_action_actual_impact']),['Actual additive impact']);
  register(fx,['Constant-currency performance']);
  register({...translation,foreign:true},['Closing FX & equity translation']);
  register({...transactions,open:true},['Exposure by transaction currency','Largest open transaction exposures']);
  register(domain('cash-entity','Entity cash',['treasury_entity_cash'],['entity']),['Cash by legal entity']);
  register(domain('sensitivity','Sensitivity detail',['financial_sensitivity_detail']),['CFO sensitivity matrix']);
  for(const [title,dataset] of Object.entries({'Expected credit loss exposure':'credit_loss_detail','Inventory provision exposure':'inventory_provision_detail','Customer aging watchlist':'ar_customer_aging','SKU aging watchlist':'inventory_sku_aging','Supplier concentration':'supplier_concentration','Supplier aging watchlist':'ap_supplier_aging','Open customer advances':'contract_liability_detail','Customer profitability':'customer_profitability'}))register(domain(dataset,'Selected detail',[dataset]),[title]);
  // These renderers are group-only even if the source itself has dimensions.
  const groupPanels=['Group management commentary','Financial position','Close priorities','Management commitments','Benefits realization','Base forecast P&L','OPEX composition','Price / Volume / Mix','Asset-quality trend','Provision impact','AR aging','Inventory aging','AP aging','Contract-liability trend','Free cash flow','Latest cash bridge','Treasury overlay','Base forecast Cash Flow','Receivables carrying value','Inventory carrying value','Funding structure','Total assets trend','Customer prepayment funding','Contract liability trend','Base forecast Balance Sheet','Rolling forecast scenarios','Forecast accuracy','Liquidity by forecast scenario','Integrated three-statement scenarios','Family economics','Quality-tier economics','SKU profitability','Catalog structure','Intercompany flow','Consolidation logic','Factory utilization','CAPEX portfolio','Portfolio decisions','Backlog trend','Bookings vs revenue','Production mix','Group prepayment trend','FTE trend','Liquidity trend','Current liquidity bridge','Debt maturity ladder','Latest cash-pool movements','Base liquidity outlook','Scenario liquidity summary','Base liquidity bridge','Translation reserve trend','Close-month macro observations','Source coverage','Group covenant sensitivity'];
  register(group,groupPanels);
  const cards=Object.create(null);
  function cardGroup(policy,labels){for(const label of labels.split('|'))cards[label]=policy;}
  cardGroup(operating,'Revenue|Gross margin|Marginal contribution|Gross profit|OPEX|EBIT');
  cardGroup(software,'ARR|NRR|GRR|New ARR|Churn ARR|Recurring mix');
  cardGroup(events,'Bookings|Recognized revenue|Ending backlog|Book-to-bill');
  cardGroup(factory,'Factory utilization|Production|Capacity headroom|Actual fixed factory cost|Absorbed fixed cost|Absorption variance');
  cardGroup(spare,'Installed base|Aftermarket revenue|Revenue / installed unit|Inventory coverage|Inventory health');
  cardGroup(workforce,'Ending FTE|Monthly hires|Monthly attrition|Personnel cost|Revenue / FTE|Personnel cost / revenue');
  cardGroup(contracts,'Contract liabilities|Open contract liabilities|Current customer advances|Latest customer advances');
  cardGroup(review,'Revenue vs budget|EBIT vs budget|FY EBIT vs budget|Adverse signals|Active actions|In progress|Overdue|Carry-forward|Closed|Cancelled');
  cardGroup(plan,'YTD revenue|YTD EBIT|FY revenue outlook|FY EBIT outlook');
  cardGroup(workforcePlan,'12M personnel cost|12M planned hires|12M ending FTE|12M target FTE');
  cardGroup(actionPlan,'Approved plans|Gross plan cases');
  cardGroup(actionBridge,'12M Revenue impact|12M EBIT impact');
  cardGroup(fx,'Revenue FX effect|EBIT FX effect');
  cardGroup(translation,'Translation reserve');
  cardGroup(transactions,'Open FX documents|Net transaction exposure|Unrealized FX P&L|Realized FX P&L');
  const card=label=>cards[label]||(/ GM$/.test(label)?operating:group);
  const panel=(view,title)=>view==='data-journey'||title==='Context & definitions'?group:(panels[title]||group);
  function rows(data,policy){
    return policy.datasets.flatMap(key=>data[key]||[]).filter(r=>{
      if(policy.activity && (r.month!==data.meta.end_month||!['revenue','gross_profit','opex','ebit','depreciation','marginal_contribution'].some(k=>typeof r[k]==='number'&&Number.isFinite(r[k])&&r[k]!==0)))return false;
      if(policy.foreign&&r.functional_currency==='EUR')return false;
      if(policy.open&&r.status!=='Open')return false;
      if(policy.overdue&&(!['Open','In Progress'].includes(r.status)||![true,'True'].includes(r.overdue)))return false;
      return true;
    });
  }
  function matches(r,scope,policy){
    const entity=policy.dimensions.includes('entity')?scope.entity:'all',division=policy.dimensions.includes('division')?scope.division:'all';
    if(policy.levels){
      const level=entity==='all'?(division==='all'?'Group':'Division'):(division==='all'?'Entity':'Entity Division');
      if(!(policy.allLevels&&entity==='all'&&division==='all')&&r.scope_level!==level)return false;
    }
    return (entity==='all'||r[policy.entityField||'entity']===entity)&&(division==='all'||r.division===division);
  }
  function resolve(data,policy,selection){
    const records=rows(data,policy),scope={entity:selection.entity||'all',division:selection.division||'all'};
    const supports=key=>policy.dimensions.includes(key);
    const exists=candidate=>records.some(r=>matches(r,candidate,policy));
    const adjusted=[];
    if(policy.dimensions.length&&!exists(scope)){
      // Keep a meaningful division before broadening the entity. Never select a different entity silently.
      if(supports('entity')&&scope.entity!=='all'){scope.entity='all';adjusted.push('entity');}
      if(!exists(scope)&&supports('division')&&scope.division!=='all'){scope.division='all';adjusted.push('division');}
    }
    const options={entity:[],division:[]};
    for(const key of ['entity','division']){
      if(!supports(key))continue;
      const known=new Set((data.management_detail||[]).map(r=>r[key]));
      for(const value of [...known].sort())if(value&&exists({...scope,[key]:value}))options[key].push(value);
    }
    return {scope,options,adjusted,empty:policy.dimensions.length>0&&!exists(scope)};
  }
  const api={group,card,panel,panels,rows,matches,resolve};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ReportContext=api;
})(globalThis);
