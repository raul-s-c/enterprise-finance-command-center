const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
const context=require('../web/report-context.js');
require('../web/supplier-risk-visual.js');
const visual=globalThis.FinanceSupplierVisual;

test('open supplier AP reconciles to the published group trade payables',()=>{
  const current=published.ap_supplier_aging.filter(row=>row.month===published.meta.end_month);
  const sum=current.reduce((value,row)=>value+Number(row.total_ap),0);
  assert.ok(Math.abs(sum-Number(published.ap_aging_summary.at(-1).total_ap))<.01);
  const html=visual.ranking(current,{key:'total_ap',kind:'ap'});
  assert.equal((html.match(/class="sr-row"/g)||[]).length,5);
  assert.match(html,/Scoped open AP/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('supplier spend ranking is source-tied and does not invent a group spend denominator',()=>{
  const rows=[{supplier_name:'<unsafe>',entity:'US01',division:'Hardware',trailing_12m_spend:2000,total_ap:300,supplier_spend_share:.2},{supplier_name:'Other',entity:'DE01',division:'Events',trailing_12m_spend:1000,total_ap:100,supplier_spend_share:.1}];
  const html=visual.ranking(rows,{key:'trailing_12m_spend',kind:'spend'});
  assert.ok(html.indexOf('&lt;unsafe&gt;')<html.indexOf('Other'));
  assert.match(html,/€2.0k/);
  assert.match(html,/not the complete group spend denominator/);
  assert.doesNotMatch(html,/<unsafe>/);
});

test('supplier filters only offer current scopes with positive open AP',()=>{
  const spend=context.panel('working-capital','Supplier concentration'),open=context.panel('working-capital','Supplier aging watchlist');
  assert.equal(spend.key,open.key);
  const records=context.rows(published,spend);
  assert.ok(records.length>0);
  assert.ok(records.every(row=>row.month===published.meta.end_month&&Number(row.total_ap)>0));
  const selections=context.resolve(published,spend,{entity:'all',division:'all'});
  for(const entity of selections.options.entity){
    const resolved=context.resolve(published,spend,{entity,division:'all'});
    assert.ok(!resolved.empty);
    for(const division of resolved.options.division)assert.ok(records.some(row=>context.matches(row,{entity,division},spend)),`${entity}/${division} lacks open AP`);
  }
});
