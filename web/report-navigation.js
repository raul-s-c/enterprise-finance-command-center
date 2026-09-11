/* Six decision areas over the existing report catalog. */
(function(root){
  const areas=[
    {id:'executive',label:'Executive',landing:'executive',description:'The monthly story and management focus.',views:['executive']},
    {id:'performance',label:'Performance',landing:'pnl',description:'Revenue, margin and profitability.',views:['pnl','margin','profitability']},
    {id:'cash-balance',label:'Cash & Balance',landing:'working-capital',description:'Cash conversion, liquidity and financial position.',views:['working-capital','cash-flow','treasury','balance-sheet']},
    {id:'plan-outlook',label:'Plan & Outlook',landing:'forecast',description:'Budget, rolling forecast and sensitivities.',views:['forecast','macro-sensitivities']},
    {id:'operations',label:'Operations',landing:'business-drivers',description:'Drivers, intercompany, assets and FX.',views:['business-drivers','intercompany','operations-capex','fx']},
    {id:'close-controls',label:'Close & Controls',landing:'close-journey',description:'Close, review, actions and evidence.',views:['close-journey','performance-review','action-execution','data-journey']}
  ];
  const areaFor=view=>areas.find(area=>area.views.includes(view))||areas[0];
  const modules=(area,available)=>area.views.map(id=>available.find(item=>item[0]===id)).filter(Boolean);
  const api={areas,areaFor,modules};
  root.ReportNavigation=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
