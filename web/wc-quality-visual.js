/* Working-capital quality: published balances first, full evidence retained. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const number=value=>Number.isFinite(Number(value))?Number(value):0;
  const money=value=>{const amount=number(value),absolute=Math.abs(amount);return `${amount<0?'−':''}€${absolute>=1e6?(absolute/1e6).toFixed(1)+'m':absolute>=1e3?(absolute/1e3).toFixed(1)+'k':new Intl.NumberFormat('en-GB',{maximumFractionDigits:0}).format(absolute)}`;};
  const percent=value=>`${(number(value)*100).toFixed(1)}%`;

  function ranked(rows,{label,amount,gross,description}){
    const positive=(rows||[]).filter(row=>number(row[amount])>0).sort((a,b)=>number(b[amount])-number(a[amount]));
    if(!positive.length)return '<p class="wq-empty">No positive reserves in this selected scope. The source schedule remains available below.</p>';
    const valid=positive.slice(0,5),total=positive.reduce((sum,row)=>sum+number(row[amount]),0),top=valid.reduce((sum,row)=>sum+number(row[amount]),0),max=number(valid[0][amount]);
    return `<div class="wq-ranked" role="list" aria-label="Five largest ${escape(description)}">
      <div class="wq-portfolio-strip"><div><span>Scoped reserve · source detail</span><strong>${money(total)}</strong></div><div><span>Top five share</span><strong>${percent(top/total)}</strong></div></div>
      ${valid.map((row,index)=>{const reserve=number(row[amount]),book=number(row[gross]),ratio=book>0?reserve/book:0;
        return `<div class="wq-rank" role="listitem" title="${escape(label(row))}: ${money(reserve)} reserve against ${money(book)} gross exposure"><b>${index+1}</b><div class="wq-rank-main"><div class="wq-rank-caption"><strong>${escape(label(row))}</strong><span>${escape(row.entity)} · ${escape(row.division)}</span></div><div class="wq-track"><i style="width:${(reserve/max*100).toFixed(2)}%"></i></div></div><div class="wq-rank-values"><strong>${money(reserve)}</strong><span>${money(book)} gross · ${percent(ratio)}</span></div></div>`;
      }).join('')}
      <p class="wq-explain">Bars compare reserve amounts within the five largest records. Gross exposure and reserve rate are shown separately; the preview is not a portfolio total.</p>
    </div>`;
  }

  function aging(summary,fields,{title,totalKey,riskKey,riskLabel}){
    const record=summary||{},total=number(record[totalKey]),values=fields.map(([,key])=>Math.max(0,number(record[key]))),bucketTotal=values.reduce((sum,value)=>sum+value,0);
    if(total<=0)return '<p class="wq-empty">No positive gross balance is published for this close.</p>';
    const difference=bucketTotal-total,matched=Math.abs(difference)<.05;
    return `<div class="wq-aging" aria-label="${escape(title)} by aging bucket">
      <div class="wq-aging-total"><span>Gross balance · group close</span><strong>${money(total)}</strong></div>
      <div class="wq-aging-stack" role="img" aria-label="${escape(fields.map(([name],index)=>`${name} ${money(values[index])}`).join('; '))}">${fields.map(([name],index)=>`<i class="wq-bucket-${index}" style="width:${(values[index]/total*100).toFixed(4)}%" title="${escape(name)}: ${money(values[index])}"></i>`).join('')}</div>
      <div class="wq-aging-legend">${fields.map(([name],index)=>`<div><i class="wq-key-${index}"></i><span>${escape(name)}</span><strong>${money(values[index])}</strong><small>${percent(values[index]/total)}</small></div>`).join('')}</div>
      <div class="wq-aging-foot"><span>${escape(riskLabel)}</span><strong>${money(record[riskKey])}</strong><small>${matched?'Buckets reconcile to the published gross balance.':`Bucket difference ${money(difference)} — inspect source schedule.`}</small></div>
    </div>`;
  }

  function trend(rows,key,label){
    const history=(rows||[]).filter(row=>Number.isFinite(Number(row[key]))).slice(-12);
    if(history.length<2)return '';
    const values=history.map(row=>number(row[key])),low=Math.min(...values),high=Math.max(...values),spread=high-low||1;
    const points=values.map((value,index)=>`${(5+index*290/(values.length-1)).toFixed(1)},${(44-(value-low)/spread*32).toFixed(1)}`).join(' ');
    return `<div class="wq-trend"><div><strong>${escape(label)} · 12-month context</strong><span>${escape(history[0].month)} ${percent(values[0])} → ${escape(history.at(-1).month)} ${percent(values.at(-1))}</span></div><svg viewBox="0 0 300 50" preserveAspectRatio="none" role="img" aria-label="${escape(label)} by month: ${escape(history.map((row,index)=>`${row.month} ${percent(values[index])}`).join('; '))}"><polyline points="${points}"/></svg></div>`;
  }

  function decorate(html,source,scope){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    // Pair the two selectable reserve panels, then the two fixed-group aging panels.
    const titled=title=>[...host.querySelectorAll('article.panel')].find(panel=>panel.querySelector('.panel-title')?.textContent.trim()===title);
    titled('Expected credit loss exposure')?.after(titled('Inventory provision exposure'));
    const current=rows=>(rows||[]).filter(row=>row.month===source.meta.end_month);
    const scoped=rows=>{let result=current(rows);if(scope.entity!=='all')result=result.filter(row=>row.entity===scope.entity);if(scope.division!=='all')result=result.filter(row=>row.division===scope.division);return result;};
    const ar=(source.ar_aging_summary||[]).at(-1),inventory=(source.inventory_aging_summary||[]).at(-1);
    const panels={
      'Expected credit loss exposure':()=>ranked(scoped(source.credit_loss_detail),{label:row=>row.customer_name,amount:'credit_loss_allowance',gross:'gross_ar',description:'customer credit-loss allowances'}),
      'Inventory provision exposure':()=>ranked(scoped(source.inventory_provision_detail),{label:row=>row.product,amount:'inventory_provision',gross:'gross_inventory',description:'SKU inventory provisions'}),
      'AR aging':()=>aging(ar,[['Current','current'],['1–30','overdue_1_30'],['31–60','overdue_31_60'],['61–90','overdue_61_90'],['>90','overdue_90_plus']],{title:'Receivables',totalKey:'total_ar',riskKey:'overdue_ar',riskLabel:'Total overdue · group'})+trend(source.ar_aging_summary,'overdue_pct','Overdue AR share'),
      'Inventory aging':()=>aging(inventory,[['0–30','age_0_30'],['31–60','age_31_60'],['61–90','age_61_90'],['91–180','age_91_180'],['>180','age_180_plus']],{title:'Inventory',totalKey:'inventory_value',riskKey:'obsolescence_risk_value',riskLabel:'Obsolescence risk · group'})+trend(source.inventory_aging_summary,'obsolescence_risk_pct','Obsolescence risk share')
    };
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();if(!panels[title])continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+panels[title]()+`<details class="wq-source"><summary>View original source schedule</summary>${original}</details>`;
      panel.classList.add('wq-panel');
    }
    return host.innerHTML;
  }

  root.FinanceWCQualityVisual={ranked,aging,trend,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers['working-capital'];
    renderers['working-capital']=function(){return decorate(before(),data,state);};
  }
})(globalThis);
