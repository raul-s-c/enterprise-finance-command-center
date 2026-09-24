/* Current published factory accounting and sell-through mix, kept at distinct grains. */
(function(root){
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const number=value=>Number(value)||0;
  const euro=value=>`${value<0?'-':''}€${(Math.abs(value)/1e6).toFixed(2)}m`;
  const percent=value=>`${(value*100).toFixed(1)}%`;
  function factory(rows){
    if(!rows.length)return '<p class="fa-empty">No current factory accounting record.</p>';
    const total=rows.reduce((sum,row)=>({actual:sum.actual+number(row.actual_fixed_factory_cost),absorbed:sum.absorbed+number(row.absorbed_fixed_cost),variance:sum.variance+number(row.absorption_variance),produced:sum.produced+number(row.produced_units),capacity:sum.capacity+number(row.capacity_units)}),{actual:0,absorbed:0,variance:0,produced:0,capacity:0});
    const scale=Math.max(...rows.flatMap(row=>[number(row.actual_fixed_factory_cost),number(row.absorbed_fixed_cost)]),1);
    return `<div class="fa-visual" aria-label="Published factory fixed-cost absorption"><div class="fa-equation"><div><span>Actual fixed cost</span><strong>${euro(total.actual)}</strong></div><b>−</b><div><span>Absorbed into output</span><strong>${euro(total.absorbed)}</strong></div><b>=</b><div class="${total.variance>=0?'fa-alert':'fa-good'}"><span>${total.variance>=0?'Under-absorption':'Over-absorption'}</span><strong>${euro(Math.abs(total.variance))}</strong></div></div><div class="fa-sites">${rows.map(row=>`<div class="fa-site"><header><strong>${escape(row.factory_name)}</strong><span>${escape(row.factory)} · ${percent(number(row.produced_units)/Math.max(number(row.capacity_units),1))} utilized</span></header><div class="fa-cost-row"><span>Actual</span><i style="width:${(number(row.actual_fixed_factory_cost)/scale*100).toFixed(2)}%"></i><b>${euro(number(row.actual_fixed_factory_cost))}</b></div><div class="fa-cost-row absorbed"><span>Absorbed</span><i style="width:${(number(row.absorbed_fixed_cost)/scale*100).toFixed(2)}%"></i><b>${euro(number(row.absorbed_fixed_cost))}</b></div><small>${escape(row.factory)} variance: ${euro(number(row.absorption_variance))} · ${number(row.absorption_variance)>=0?'charged to gross profit':'released to gross profit'}</small></div>`).join('')}</div><p class="fa-reconcile ${Math.abs(total.actual-total.absorbed-total.variance)<.01?'fa-good':'fa-alert'}">Actual − absorbed − posted variance: ${euro(Math.abs(total.actual-total.absorbed-total.variance))} · ${Math.abs(total.actual-total.absorbed-total.variance)<.01?'reconciled':'review difference'}</p></div>`;
  }
  function mix(rows){
    if(!rows.length)return '<p class="fa-empty">No published source-factory sales mix.</p>';
    const byFamily=new Map();
    for(const row of rows){
      const key=`${row.source_factory} · ${row.product_family}`;
      byFamily.set(key,(byFamily.get(key)||0)+number(row.units));
    }
    const ordered=[...byFamily].sort((a,b)=>b[1]-a[1]);
    const total=ordered.reduce((sum,[,units])=>sum+units,0),maximum=Math.max(...ordered.map(([,units])=>units),1);
    const top=ordered.slice(0,6);
    if(ordered.length>6)top.push([`Other ${ordered.length-6} factory/family combinations`,ordered.slice(6).reduce((sum,[,units])=>sum+units,0)]);
    return `<div class="fa-visual" aria-label="Published source-factory sales mix"><div class="fa-mix-total"><span>Units in external sales</span><strong>${total.toLocaleString('en-US')}</strong></div><div class="fa-mix-list">${top.map(([label,units])=>`<div class="fa-mix-row"><span title="${escape(label)}">${escape(label)}</span><div><i style="width:${(units/maximum*100).toFixed(2)}%"></i></div><b>${units.toLocaleString('en-US')}</b></div>`).join('')}</div><p class="fa-note">Sales mix is not current-month factory output. Published source rows remain below; do not reconcile these units to production.</p></div>`;
  }
  function decorate(html,source){
    if(!root.document)return html;
    const host=document.createElement('div');host.innerHTML=html;
    for(const panel of host.querySelectorAll('article.panel')){
      const title=panel.querySelector('.panel-title')?.textContent.trim();
      if(!['Factory absorption accounting','Production mix'].includes(title))continue;
      const head=panel.querySelector('.panel-head');if(!head)continue;
      const original=[...panel.children].filter(child=>child!==head).map(child=>child.outerHTML).join('');
      const rows=title==='Factory absorption accounting'?(source.hardware_factory_economics||[]).filter(row=>row.month===source.meta.end_month):(source.hardware_mix||[]).filter(row=>row.month===source.meta.end_month);
      panel.innerHTML=head.outerHTML+(title==='Factory absorption accounting'?factory(rows):mix(rows))+`<details class="fa-source"><summary>View published source table</summary>${original}</details>`;
      panel.classList.add('fa-panel');
    }
    return host.innerHTML;
  }
  root.FinanceFactoryVisual={factory,mix,decorate};
  if(root.document&&typeof renderers!=='undefined'){
    const before=renderers['business-drivers'];
    renderers['business-drivers']=function(){return decorate(before(),data);};
  }
})(globalThis);
