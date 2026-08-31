const eur = new Intl.NumberFormat('en-US',{style:'currency',currency:'EUR',notation:'compact',maximumFractionDigits:1});

Promise.all([
  fetch('data/summary.json').then(r=>r.json()),
  fetch('data/forecast.json').then(r=>r.json()),
  fetch('data/manifest.json').then(r=>r.json())
]).then(([actual, forecast, manifest])=>{
  const latest=actual[actual.length-1];
  const prev=actual[actual.length-2];
  const margin=latest.ebit/latest.revenue;
  const gp=latest.gross_profit/latest.revenue;
  const growth=(latest.revenue/prev.revenue)-1;
  document.getElementById('status').textContent=`Closed through ${manifest.end_month}`;
  document.getElementById('kpis').innerHTML=[
    ['Revenue',eur.format(latest.revenue)],
    ['Gross margin',(gp*100).toFixed(1)+'%'],
    ['EBIT',eur.format(latest.ebit)],
    ['Revenue MoM',(growth*100).toFixed(1)+'%']
  ].map(([l,v])=>`<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div></div>`).join('');
  const tail=actual.slice(-18);
  const max=Math.max(...tail.map(d=>d.revenue));
  document.getElementById('chart').innerHTML=tail.map((d,i)=>`<div class="bar-wrap"><div class="bar ${i===tail.length-1?'latest':''}" style="height:${Math.max(4,d.revenue/max*220)}px" title="${d.month}: ${eur.format(d.revenue)}"></div><div class="month">${d.month}</div></div>`).join('');
  const c=manifest.validation;
  document.getElementById('controls').innerHTML=`<p class="${c.passed?'ok':'bad'}">${c.passed?'PASS':'FAIL'}: accounting controls</p><p>Maximum journal gap: EUR ${c.journal_balance_max_gap.toFixed(2)}</p><p>Trial balance gap: EUR ${c.trial_balance_gap.toFixed(2)}</p><p>${manifest.journal_rows.toLocaleString()} journal lines generated.</p>`;
}).catch(err=>{
  document.getElementById('status').textContent='Dataset not built yet';
  document.getElementById('controls').textContent=String(err);
});
