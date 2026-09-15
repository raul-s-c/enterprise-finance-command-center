/* Source-tied graphical income statement. No invented account allocations. */
(function(root){
  function rows(ac,py,M){
    ac=ac||{};py=py||{};
    const extend=row=>[...M.statement(row),{key:'below_ebit',label:'Net finance costs and tax',cost:true,value:M.finite(row.ebit)&&M.finite(row.net_income)?row.ebit-row.net_income:null},{key:'net_income',label:'Net income',total:true,value:row.net_income}];
    const previous=extend(py);let running=0;
    return extend(ac).map((r,i)=>{const start=r.total?0:running,end=r.total?r.value:M.finite(r.value)&&M.finite(running)?running-r.value:null;running=end;return {...r,start,end,prior:previous[i].value,change:M.variance(r.value,previous[i].value,r.cost?-1:1)};});
  }
  function render(ac,py,month,scope){
    const M=root.FinanceReport,esc=M.escape,items=rows(ac,py,M),max=Math.max(1,...items.flatMap(r=>[Math.abs(r.start||0),Math.abs(r.end||0)])),deltaMax=Math.max(1,...items.map(r=>Math.abs(r.change.delta||0))),pctMax=Math.max(.01,...items.map(r=>Math.abs(r.change.relative||0)));
    const amount=v=>M.finite(v)?(Math.abs(v)>=1e6?`${(v/1e6).toFixed(1)}M`:`${(v/1e3).toFixed(1)}K`):'—',signed=v=>M.finite(v)?`${v>0?'+':''}${amount(v)}`:'—';
    return `<article class="pnl-visual"><header><h2>Income statement · Actual vs prior year</h2><p>${esc(month)} · EUR million · ${esc(scope)} · Select a line for its calculation</p></header><div class="pnl-scroll" tabindex="0" role="region" aria-label="Graphical income statement; scroll to explore all columns"><div class="pnl-grid"><div class="pnl-heading"><span>Income statement</span><span>PY</span><span>AC · income bridge</span><span>Δ PY</span><span>Δ PY %</span></div>${items.map(r=>{const tone=r.change.favorable===true?'good':r.change.favorable===false?'bad':'neutral',left=50+Math.min(r.start||0,r.end||0)/max*42,width=Math.abs((r.end||0)-(r.start||0))/max*42;return `<button class="pnl-row ${r.total?'subtotal':''}" data-pnl-key="${r.key}" aria-label="${esc(r.label)}: actual ${amount(r.value)}, prior year ${amount(r.prior)}"><span>${r.total?'= ':'− '}${esc(r.label)}</span><span>${amount(r.prior)}</span><span class="pnl-track"><i style="left:${left}%;width:${width}%"></i><b>${amount(r.value)}</b></span><span class="pnl-delta ${tone}"><i style="left:${r.change.delta<0?50-Math.abs(r.change.delta)/deltaMax*45:50}%;width:${Math.abs(r.change.delta||0)/deltaMax*45}%"></i><b>${signed(r.change.delta)}</b></span><span class="pnl-percent ${tone}"><i style="left:${r.change.relative<0?50-Math.abs(r.change.relative)/pctMax*45:50}%;width:${Math.abs(r.change.relative||0)/pctMax*45}%"></i><b>${M.finite(r.change.relative)?`${r.change.relative>0?'+':''}${(r.change.relative*100).toFixed(1)}%`:'—'}</b></span></button>`;}).join('')}</div></div><p class="pnl-note">Green = favorable; red = unfavorable. Costs use lower-is-better. Net finance costs and tax are shown together because this operating dataset does not provide their separate allocation.</p></article>`;
  }
  function contributions(data,scope,key,M){
    const groups=new Map();
    for(const row of data.management_detail||[]){
      if(scope.entity!=='all'&&scope.entity!==row.entity)continue;
      if(scope.division!=='all'&&scope.division!==row.division)continue;
      if(![data.meta.end_month,M.priorMonth(data.meta.end_month)].includes(row.month))continue;
      const id=JSON.stringify([row.entity,row.division]);
      if(!groups.has(id))groups.set(id,[]);
      groups.get(id).push(row);
    }
    return [...groups.values()].map(source=>{
      const months=M.aggregate(source),ac=months.find(r=>r.month===data.meta.end_month),py=months.find(r=>r.month===M.priorMonth(data.meta.end_month));
      const line=rows(ac,py,M).find(r=>r.key===key);
      return {entity:source[0].entity,division:source[0].division,actual:line?.value??null,prior:line?.prior??null,change:line?.change,records:source.filter(r=>r.month===data.meta.end_month).length};
    }).sort((a,b)=>Math.abs(b.actual||0)-Math.abs(a.actual||0));
  }
  function detail(data,scope,key){
    const M=root.FinanceReport,esc=M.escape,parts=contributions(data,scope,key,M),max=Math.max(1,...parts.map(r=>Math.abs(r.actual||0)));
    const precise=v=>M.finite(v)?(v/1e6).toLocaleString('en-GB',{minimumFractionDigits:3,maximumFractionDigits:6}):'—';
    const C={money:precise,signed:v=>M.finite(v)?`${v>0?'+':''}${precise(v)}`:'—'};
    return `<section class="pnl-source-detail"><h3>Contribution by entity and division</h3><p>Published management summary records, not individual ledger postings. Select a scope to explore its full P&amp;L.</p><div class="pnl-source-scroll"><table><thead><tr><th>Entity / division</th><th>AC (€m)</th><th>PY (€m)</th><th>Δ (€m)</th><th>Contribution magnitude</th></tr></thead><tbody>${parts.map(r=>`<tr><th><button data-pnl-entity="${esc(r.entity)}" data-pnl-division="${esc(r.division)}">${esc(r.entity)} / ${esc(r.division)}</button></th><td>${C.money(r.actual)}</td><td>${C.money(r.prior)}</td><td>${C.signed(r.change?.delta)}</td><td><span class="pnl-source-bar" aria-label="${r.actual<0?'Negative':'Positive'} contribution"><i style="width:${Math.abs(r.actual||0)/max*100}%;background:${r.actual<0?'#c82028':'#0874ed'}"></i></span></td></tr>`).join('')}</tbody></table></div><p>${parts.reduce((n,r)=>n+r.records,0)} current-period source rows · Missing comparisons remain unavailable, not zero. Bar length shows magnitude; signs are retained in the values.</p></section>`;
  }
  const api={rows,render,contributions,detail};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PnlVisual=api;
})(globalThis);
