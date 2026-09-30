const {test}=require('node:test');
const assert=require('node:assert/strict');
global.FinanceReport={escape:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')};
const visual=require('../web/performance-review-visual.js');
const data=require('../web/data/dashboard.json');

test('review overview uses the selected published scope, not overlapping levels',()=>{
  const group=visual.scope(data.performance_review,{entity:'all',division:'all'});
  const hardware=visual.scope(data.performance_review,{entity:'US01',division:'Hardware'});
  assert.equal(group.length,17);
  assert.equal(hardware.length,6);
  assert.ok(group.every(row=>row.scope_level==='Group'));
  assert.ok(hardware.every(row=>row.scope_level==='Entity Division'&&row.entity==='US01'&&row.division==='Hardware'));
  const groupPage=visual.page(data,{entity:'all',division:'all'});
  const hardwarePage=visual.page(data,{entity:'US01',division:'Hardware'});
  assert.match(groupPage,/Revenue bridge · PY to actual/);
  assert.match(groupPage,/FY EBIT vs budget/);
  assert.doesNotMatch(hardwarePage,/Revenue bridge · PY to actual|FY EBIT vs budget/);
  assert.match(hardwarePage,/US01 \/ Hardware OPEX/);
});

test('price-volume-mix bars appear only when the published bridge reconciles',()=>{
  const group=visual.scope(data.performance_review,{entity:'all',division:'all'});
  const html=visual.bridge(group,data,{entity:'all',division:'all'});
  assert.equal((html.match(/class="prv-bridge-column"/g)||[]).length,5);
  const effects=['Price effect','Volume effect','Mix effect'].map(metric=>group.find(row=>row.metric===metric).actual_value);
  const current=data.meta.end_month,prior=`${Number(current.slice(0,4))-1}${current.slice(4)}`;
  const revenue=month=>data.management_detail.filter(row=>row.month===month).reduce((sum,row)=>sum+row.revenue,0);
  assert.ok(Math.abs(revenue(prior)+effects.reduce((sum,value)=>sum+value,0)-revenue(current))<0.01);
  assert.match(html,/price_volume_mix\.csv/);
  assert.doesNotMatch(html,/NaN|undefined/);
  const changed=group.map(row=>row.metric==='Mix effect'?{...row,actual_value:row.actual_value+1}:row);
  assert.equal(visual.bridge(changed,data,{entity:'all',division:'all'}),'');
  assert.equal(visual.bridge(group,data,{entity:'US01',division:'Hardware'}),'');
});

test('review values keep their financial sign and escape source text',()=>{
  assert.equal(visual.amount(-1042179.7333),'-€1.0m');
  assert.equal(visual.amount(593891.01),'€593.9k');
  const changed={...data,performance_review:[{...data.performance_review[0],headline:'<unsafe>'}]};
  assert.doesNotMatch(visual.page(changed,{entity:'all',division:'all'}),/<unsafe>/);
});
