/* Supplier spend, open AP and maturity from one published close. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const number=value=>Number.isFinite(Number(value))?Number(value):0;
  const money=value=>{const amount=number(value),absolute=Math.abs(amount);return `${amount<0?'−':''}€${absolute>=1e6?(absolute/1e6).toFixed(1)+'m':absolute>=1e3?(absolute/1e3).toFixed(1)+'k':new Intl.NumberFormat('en-GB',{maximumFractionDigits:0}).format(absolute)}`;};
  const percent=value=>`${(number(value)*100).toFixed(1)}%`;

  function ranking(rows,{key,kind}){
    const all=(rows||[]).filter(row=>number(row[key])>0).sort((a,b)=>number(b[key])-number(a[key]));
    if(!all.length)return '<p class="sr-empty">No positive supplier balance in this selection; inspect the source schedule below.</p>';
    const leaders=all.slice(0,5),max=number(leaders[0][key]),total=all.reduce((sum,row)=>sum+number(row[key]),0),top=leaders.reduce((sum,row)=>sum+number(row[key]),0);
    const isSpend=kind==='spend';
    return `<div class="sr-visual" role="list" aria-label="Top five suppliers by ${isSpend?'trailing 12-month spend':'open trade payables'}">
      <div class="sr-summary"><div><span>${isSpend?'Selected source records · 12M spend':'Scoped open AP · source detail'}</span><strong>${money(total)}</strong></div><div><span>Top five share of source detail</span><strong>${percent(top/total)}</strong></div></div>
      ${leaders.map((row,index)=>{const value=number(row[key]);return `<div class="sr-row" role="listitem" title="${escape(row.supplier_name)}: ${money(value)} ${isSpend?'trailing spend':'open AP'}"><b>${index+1}</b><div class="sr-main"><div class="sr-caption"><strong>${escape(row.supplier_name)}</strong><span>${escape(row.entity)} · ${escape(row.division)}</span></div><div class="sr-track"><i style="width:${(value/max*100).toFixed(2)}%"></i></div></div><div class="sr-values"><strong>${money(value)}</strong><span>${isSpend?`${money(row.total_ap)} open AP · source share ${percent(row.supplier_spend_share)}`:`${number(row.payment_terms_days)}d terms · ${row.single_source?'Single source':number(row.supplier_criticality)>=4?'Critical supplier':'Standard'}`}</span></div></div>`;}).join('')}
      <p class="sr-note">${isSpend?'Spend and supplier share are source fields. The listed records are not the complete group spend denominator.':'Open AP is a stock balance; payment terms and criticality are operating attributes, not a credit-loss provision.'}</p>
    </div>`;
  }

  function ageTrend(rows){
    const history=(rows||[]).filter(row=>Number.isFinite(Number(row.weighted_age_days))).slice(-12);
    if(history.length<2)return '';
    const values=history.map(row=>number(row.weighted_age_days)),low=Math.min(...values),high=Math.max(...values),span=high-low||1;
    const points=values.map((value,index)=>`${(5+index*290/(values.length-1)).toFixed(1)},${(44-(value-low)/span*32).toFixed(1)}`).join(' ');
    return `<div class="sr-trend"><div><strong>Weighted AP age · 12-month context</strong><span>${escape(history[0].month)} ${values[0].toFixed(1)}d → ${escape(history.at(-1).month)} ${values.at(-1).toFixed(1)}d</span></div><svg viewBox="0 0 300 50" preserveAspectRatio="none" role="img" aria-label="Weighted payable age by month: ${escape(history.map((row,index)=>`${row.month} ${values[index].toFixed(1)} days`).join('; '))}"><polyline points="${points}"/></svg></div>`;
  }

  function decorate(html,source,scope){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    const titled=title=>[...host.querySelectorAll('article.panel')].find(panel=>panel.querySelector('.panel-title')?.textContent.trim()===title);
    const aging=titled('AP aging'),concentration=titled('Supplier concentration'),watchlist=titled('Supplier aging watchlist');
    if(aging&&concentration&&watchlist)watchlist.after(aging); // selected supplier panels precede fixed-group AP maturity
    const scoped=rows=>(rows||[]).filter(row=>(!row.month||row.month===source.meta.end_month)&&(scope.entity==='all'||row.entity===scope.entity)&&(scope.division==='all'||row.division===scope.division));
    const ap=(source.ap_aging_summary||[]).at(-1);
    const panels={
      'Supplier concentration':()=>ranking(scoped(source.supplier_concentration),{key:'trailing_12m_spend',kind:'spend'}),
      'Supplier aging watchlist':()=>ranking(scoped(source.ap_supplier_aging),{key:'total_ap',kind:'ap'}),
      'AP aging':()=>root.FinanceWCQualityVisual.aging(ap,[['Current','current'],['1–30','overdue_1_30'],['31–60','overdue_31_60'],['61–90','overdue_61_90'],['>90','overdue_90_plus']],{title:'Trade payables',totalKey:'total_ap',riskKey:'overdue_ap',riskLabel:'Overdue supplier AP · group'})+ageTrend(source.ap_aging_summary)
    };
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();if(!panels[title])continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      panel.innerHTML=head.outerHTML+panels[title]()+`<details class="wq-source"><summary>View original source table</summary>${original}</details>`;
      panel.classList.add('sr-panel');
    }
    return host.innerHTML;
  }

  root.FinanceSupplierVisual={ranking,ageTrend,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers['working-capital'];
    renderers['working-capital']=function(){return decorate(before(),data,state);};
  }
})(globalThis);
