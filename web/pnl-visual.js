/* Source-tied graphical income statement. No invented account allocations. */
(function(root){
  let mobileView='values';
  const formulas={variable:'Revenue − marginal contribution',fixed:'Marginal contribution − gross profit',below_ebit:'EBIT − net income',revenue:'Sum of revenue',marginal_contribution:'Revenue − variable costs',gross_profit:'Marginal contribution − fixed production costs',opex:'Sum of OPEX',depreciation:'Sum of depreciation',ebit:'Gross profit − OPEX − depreciation',net_income:'EBIT − net finance costs and tax'};
  function rows(ac,py,M){
    ac=ac||{};py=py||{};
    const extend=row=>[...M.statement(row),{key:'below_ebit',label:'Net finance costs and tax',cost:true,value:M.finite(row.ebit)&&M.finite(row.net_income)?row.ebit-row.net_income:null},{key:'net_income',label:'Net income',total:true,value:row.net_income}];
    const previous=extend(py);let running=0;
    return extend(ac).map((r,i)=>{const start=r.total?0:running,end=r.total?r.value:M.finite(r.value)&&M.finite(running)?running-r.value:null;running=end;return {...r,start,end,prior:previous[i].value,change:M.variance(r.value,previous[i].value,r.cost?-1:1)};});
  }
  function render(ac,py,month,scope){
    const M=root.FinanceReport,esc=M.escape,items=rows(ac,py,M),max=Math.max(1,...items.flatMap(r=>[Math.abs(r.start||0),Math.abs(r.end||0)])),deltaMax=Math.max(1,...items.map(r=>Math.abs(r.change.delta||0))),pctMax=Math.max(.01,...items.map(r=>Math.abs(r.change.relative||0)));
    const amount=v=>M.finite(v)?(Math.abs(v)>=1e6?`${(v/1e6).toFixed(1)}M`:`${(v/1e3).toFixed(1)}K`):'—',signed=v=>M.finite(v)?`${v>0?'+':''}${amount(v)}`:'—';
    const bar=(start,end,scale,span)=>M.finite(start)&&M.finite(end)?`<i style="left:${50+Math.min(start,end)/scale*span}%;width:${Math.abs(end-start)/scale*span}%"></i>`:'';
    const body=items.map(r=>{
      const tone=r.change.favorable===true?'good':r.change.favorable===false?'bad':'neutral';
      const relative=r.change.relative,sign=relative<0?'negative':'positive';
      return `<button class="pnl-row ${r.total?'subtotal':''}" data-pnl-key="${r.key}" data-line-type="${r.total?'total':r.cost?'cost':'income'}" aria-label="${esc(r.label)}: actual ${amount(r.value)}, prior year ${amount(r.prior)}, variance ${signed(r.change.delta)}${M.finite(relative)?`, variance percent ${(relative*100).toFixed(1)}%`:''}">
        <span>${r.total?'= ':'− '}${esc(r.label)}</span><span>${amount(r.prior)}</span>
        <span class="pnl-track">${bar(r.start,r.end,max,42)}<b>${amount(r.value)}</b></span>
        <span class="pnl-delta ${tone}">${bar(0,r.change.delta,deltaMax,45)}<b>${signed(r.change.delta)}</b></span>
        <span class="pnl-percent ${tone} ${sign}">${bar(0,relative,pctMax,45)}<b>${M.finite(relative)?`${relative>0?'+':''}${(relative*100).toFixed(1)}%`:'—'}</b></span>
      </button>`;
    }).join('');
    return `<article class="pnl-visual" data-mobile-view="${mobileView}"><header><h2><span class="pnl-title-full">Income statement · Actual vs prior year</span><span class="pnl-title-compact">P&amp;L · Actual vs PY</span></h2><div class="pnl-mobile-switch" role="group" aria-label="Compact P&L columns"><button type="button" data-pnl-mobile-view="values" aria-pressed="${mobileView==='values'}">Values</button><button type="button" data-pnl-mobile-view="variance" aria-pressed="${mobileView==='variance'}">Δ PY</button></div><p><span class="pnl-values-context">${esc(month)} · EUR million · ${esc(scope)} · Select a line to inspect calculation and source</span><span class="pnl-variance-context">${esc(month)} · ${esc(scope)} · Δ vs PY; green = favorable, red = adverse</span></p></header><div class="pnl-scroll" tabindex="0" role="region" aria-label="Graphical income statement; compact columns can be changed with the Values and variance buttons"><div class="pnl-grid"><div class="pnl-heading"><span>Income statement</span><span>PY</span><span><span class="pnl-title-full">Actual · cumulative bridge</span><span class="pnl-title-compact">AC</span></span><span>Δ PY</span><span>Δ PY %</span></div>${body}</div></div><p class="pnl-note">Variance colour reflects earnings impact; cost lines use lower-is-favourable logic. Net finance costs and tax are shown together because the published operating dataset does not support a separate allocation.</p></article>`;
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
      return {entity:source[0].entity,division:source[0].division,actual:line?.value??null,prior:line?.prior??null,change:line?.change,cost:Boolean(line?.cost),records:source.filter(r=>r.month===data.meta.end_month).length};
    }).sort((a,b)=>Math.abs(b.actual||0)-Math.abs(a.actual||0));
  }
  function detail(data,scope,key){
    const M=root.FinanceReport,esc=M.escape,impact=r=>M.finite(r.change?.delta)?r.change.delta*(r.cost?-1:1):null,parts=contributions(data,scope,key,M).sort((a,b)=>Math.abs(impact(b)||0)-Math.abs(impact(a)||0)),visibleParts=parts.filter(r=>!(M.finite(r.actual)&&M.finite(r.prior)&&r.actual===0&&r.prior===0)),zeroActivity=parts.length-visibleParts.length,impactMax=Math.max(1,...visibleParts.map(r=>Math.abs(impact(r)||0)));
    const precise=v=>M.finite(v)?(v/1e6).toLocaleString('en-GB',{minimumFractionDigits:3,maximumFractionDigits:6}):'—';
    const display=v=>{if(!M.finite(v))return '—';const magnitude=Math.abs(v),digits=magnitude>=1e6?1:magnitude>=1e5?2:magnitude>=1e3?3:6;return (v/1e6).toLocaleString('en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits});};
    const exactEUR=v=>M.finite(v)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(v):'Unavailable';
    const signedDisplay=v=>M.finite(v)?`${v>0?'+':''}${display(v)}`:'—';
    const valueCell=(v,label)=>`<td title="Exact: ${esc(exactEUR(v))}" aria-label="${label}: ${esc(exactEUR(v))}">${display(v)}</td>`;
    const varianceCell=v=>`<td title="Exact: ${esc(exactEUR(v))}" aria-label="Variance: ${esc(exactEUR(v))}">${signedDisplay(v)}</td>`;
    const C={money:precise,signed:v=>M.finite(v)?`${v>0?'+':''}${precise(v)}`:'—'};
    return `<section class="pnl-source-detail"><h3>Contribution by entity and division</h3><p>Published management summary records, not individual ledger postings. Select a scope to explore its full P&amp;L.</p>${visibleParts.length?`<div class="pnl-source-scroll"><table><thead><tr><th>Entity / division</th><th>AC (€m)</th><th>PY (€m)</th><th>Δ (€m)</th><th>Variance contribution (profit impact)</th></tr></thead><tbody>${visibleParts.map(r=>`<tr><th><button data-pnl-entity="${esc(r.entity)}" data-pnl-division="${esc(r.division)}">${esc(r.entity)} / ${esc(r.division)}</button></th>${valueCell(r.actual,'Actual')}${valueCell(r.prior,'Prior year')}${varianceCell(r.change?.delta)}<td><span class="pnl-source-bar" aria-label="${impact(r)===null?'Earnings impact unavailable':impact(r)===0?'No earnings impact':impact(r)<0?'Negative':'Positive'} earnings impact: ${C.signed(impact(r))} EUR m"><i style="width:${Math.abs(impact(r)||0)/impactMax*100}%;background:${impact(r)<0?'#b42318':impact(r)>0?'#067647':'#5e6875'}"></i></span></td></tr>`).join('')}</tbody></table></div>`:`<p class="pnl-source-empty">No current or prior-year activity for this line in the selected scope.</p>`}<p>${parts.reduce((n,r)=>n+r.records,0)} current-period source rows · ${zeroActivity?`${zeroActivity} zero-activity ${zeroActivity===1?'combination':'combinations'} omitted from this view and retained in CSV export. `:''}Missing comparisons remain unavailable, not zero. Bars show profit impact versus PY; cost increases are adverse and cost reductions favorable. AC, PY and Δ values retain source signs.</p></section>`;
  }
  function inspector(data,scope,key){
    const M=root.FinanceReport,esc=M.escape,period=data.meta.end_month;
    const source=(data.management_detail||[]).filter(row=>(scope.entity==='all'||row.entity===scope.entity)&&(scope.division==='all'||row.division===scope.division));
    const months=M.aggregate(source),actual=months.find(row=>row.month===period),prior=months.find(row=>row.month===M.priorMonth(period));
    const line=rows(actual,prior,M).find(row=>row.key===key);
    if(!line)return '<p>No source-backed P&amp;L line is available for this selection.</p>';
    const format=value=>M.finite(value)?`${value<0?'-':''}€${Math.abs(value)>=1e6?(Math.abs(value)/1e6).toFixed(1)+'m':(Math.abs(value)/1e3).toFixed(1)+'k'}`:'—';
    const signed=value=>M.finite(value)?`${value>0?'+':''}${format(value)}`:'—';
    const profitImpact=part=>M.finite(part.change?.delta)?part.change.delta*(part.cost?-1:1):null,parts=contributions(data,scope,key,M).sort((a,b)=>Math.abs(profitImpact(b)||0)-Math.abs(profitImpact(a)||0)),largest=Math.max(1,...parts.map(part=>Math.abs(profitImpact(part)||0)));
    const sourceTotal=parts.reduce((total,part)=>total+(part.actual||0),0),gap=M.finite(line.value)?line.value-sourceTotal:null;
    const difference=M.finite(gap)&&Math.abs(gap)>0.02?`Source-to-scope difference ${signed(gap)}; no balancing adjustment is applied.`:'Entity/division source rows reconcile to the selected line.';
    return `<div class="pnl-inspector-head"><div><small>SELECTED P&amp;L LINE</small><h3>${esc(line.label)}</h3></div><button type="button" data-pnl-open-evidence aria-label="Open full ${esc(line.label)} evidence">Full evidence ${'<span aria-hidden="true">↗</span>'}</button></div>
      <div class="pnl-inspector-value"><strong>${format(line.value)}</strong><span class="${line.change.favorable===true?'good':line.change.favorable===false?'bad':'neutral'}">${signed(line.change.delta)} vs PY</span></div>
      <dl class="pnl-inspector-math"><div><dt>Prior year</dt><dd>${format(line.prior)}</dd></div><div><dt>Calculation</dt><dd>${esc(formulas[key]||'Published P&L measure')}</dd></div><div><dt>Source</dt><dd>management_detail · management summary</dd></div></dl>
      <div class="pnl-inspector-rank"><h4>Contribution by entity / division</h4>${parts.slice(0,5).map(part=>`<div class="pnl-inspector-part"><span>${esc(part.entity)} / ${esc(part.division)}</span><b>${profitImpact(part)===null?'—':`${signed(profitImpact(part))} vs PY`}</b><i aria-hidden="true"><span style="width:${Math.abs(profitImpact(part)||0)/largest*100}%;background:${profitImpact(part)<0?'#b42318':profitImpact(part)>0?'#067647':'#5e6875'}"></span></i></div>`).join('')}${parts.length>5?`<p>+${parts.length-5} more in full evidence</p>`:''}</div>
      <p class="pnl-inspector-control">${esc(difference)} These are management summary records, not individual ledger postings.</p>`;
  }
  function csv(data,scope,key,M=root.FinanceReport){
    const cell=value=>{
      if(typeof value==='number')return Number.isFinite(value)?String(value):'';
      let text=String(value??'');
      if(/^[\s]*[=+\-@]/.test(text))text="'"+text;
      return `"${text.replaceAll('"','""')}"`;
    };
    const header=['period','comparison_period','line','entity','division','actual_eur','prior_eur','variance_eur','variance_ratio','current_source_rows','source'];
    return [header,...contributions(data,scope,key,M).map(r=>[data.meta.end_month,M.priorMonth(data.meta.end_month),key,r.entity,r.division,r.actual,r.prior,r.change?.delta,r.change?.relative,r.records,'management_detail'])].map(row=>row.map(cell).join(',')).join('\r\n');
  }
  const api={rows,render,contributions,detail,inspector,formulas,csv};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PnlVisual=api;
  if(root.document)document.addEventListener('click',event=>{
    const button=event.target.closest('[data-pnl-mobile-view]');if(!button)return;
    const article=button.closest('.pnl-visual');if(!article)return;
    mobileView=button.dataset.pnlMobileView==='variance'?'variance':'values';
    article.dataset.mobileView=mobileView;
    for(const choice of article.querySelectorAll('[data-pnl-mobile-view]'))choice.setAttribute('aria-pressed',String(choice.dataset.pnlMobileView===mobileView));
  });
})(globalThis);
