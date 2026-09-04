/* Pure presentation calculations. Never modifies the published finance dataset. */
(function(root){
  const fields=['revenue','marginal_contribution','gross_profit','opex','depreciation','ebit','net_income'];
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function aggregate(rows,scope={}){
    const months=new Map();
    for(const row of rows||[]){
      if(scope.entity&&scope.entity!=='all'&&row.entity!==scope.entity)continue;
      if(scope.division&&scope.division!=='all'&&row.division!==scope.division)continue;
      const total=months.get(row.month)||Object.fromEntries([['month',row.month],...fields.map(k=>[k,0])]);
      for(const key of fields)total[key]=finite(total[key])&&finite(row[key])?total[key]+row[key]:null;
      months.set(row.month,total);
    }
    return [...months.values()].sort((a,b)=>a.month.localeCompare(b.month));
  }
  function variance(actual,comparison,polarity=1){
    if(!finite(actual)||!finite(comparison))return {delta:null,relative:null,favorable:null};
    const delta=actual-comparison;
    return {delta,relative:comparison===0?null:delta/Math.abs(comparison),favorable:delta===0?null:delta*polarity>0};
  }
  const priorMonth=month=>`${Number(month.slice(0,4))-1}${month.slice(4)}`;
  function comparisons(rows,metric,endMonth,count=12){
    const byMonth=new Map(rows.map(r=>[r.month,r]));
    return rows.filter(r=>r.month<=endMonth).slice(-count).map(r=>({month:r.month,actual:r[metric],prior:byMonth.get(priorMonth(r.month))?.[metric]??null}));
  }
  function statement(row){
    if(!row)return [];
    const difference=(a,b)=>finite(row[a])&&finite(row[b])?row[a]-row[b]:null;
    return [
      {key:'revenue',label:'Revenue',value:row.revenue,total:true},
      {key:'variable',label:'Variable costs',value:difference('revenue','marginal_contribution'),cost:true},
      {key:'marginal_contribution',label:'Marginal contribution',value:row.marginal_contribution,total:true},
      {key:'fixed',label:'Fixed production cost',value:difference('marginal_contribution','gross_profit'),cost:true},
      {key:'gross_profit',label:'Gross profit',value:row.gross_profit,total:true},
      {key:'opex',label:'OPEX',value:row.opex,cost:true},
      {key:'depreciation',label:'Depreciation',value:row.depreciation,cost:true},
      {key:'ebit',label:'EBIT',value:row.ebit,total:true}
    ];
  }
  function bridge(row){
    let running=0;
    return statement(row).map(item=>{
      const start=item.total?0:running;
      const end=item.total?item.value:finite(running)&&finite(item.value)?running-item.value:null;
      running=end;
      return {...item,start,end};
    });
  }
  function page(items,index,size){
    size=Math.max(1,Math.floor(size)||1);
    const count=Math.max(1,Math.ceil(items.length/size));
    index=Math.max(0,Math.min(count-1,Math.floor(index)||0));
    return {items:items.slice(index*size,(index+1)*size),index,count,total:items.length,size};
  }
  const pageIndex=value=>Number.isFinite(Number(value))?Math.max(0,Math.floor(Number(value))):0;
  const api={fields,finite,escape,aggregate,variance,priorMonth,comparisons,statement,bridge,page,pageIndex};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.FinanceReport=api;
})(globalThis);
