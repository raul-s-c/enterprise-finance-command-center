const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
require('../web/capex-cash-transfer-visual.js');
const visual=globalThis.FinanceCapexVisual;

test('portfolio cash spend excludes noncash GO_LIVE transfer',()=>{
  const rows=visual.projects(published.capex);
  const spend=published.capex.filter(row=>row.event==='SPEND').reduce((sum,row)=>sum+Number(row.amount),0);
  const transfer=published.capex.filter(row=>row.event==='GO_LIVE').reduce((sum,row)=>sum+Number(row.amount),0);
  assert.ok(Math.abs(rows.reduce((sum,row)=>sum+row.spend,0)-spend)<.01);
  assert.ok(Math.abs(rows.reduce((sum,row)=>sum+row.transfer,0)-transfer)<.01);
  assert.ok(Math.abs(spend-transfer-rows.reduce((sum,row)=>sum+row.cip,0))<.01);
  assert.ok(rows.every(row=>row.cip>=-.05));
  assert.ok(transfer>0);
});

test('portfolio explains accounting events without treating go-live as cash',()=>{
  const html=visual.visual(visual.projects(published.capex));
  assert.match(html,/SPEND: Dr 1510 CIP · Cr 1000 Cash/);
  assert.match(html,/GO_LIVE: Dr 1500 PPE · Cr 1510 CIP/);
  assert.match(html,/GO_LIVE is not another cash outflow/);
  assert.match(html,/reconciled/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('project names are escaped',()=>{
  const html=visual.visual([{project:'P1',name:'<unsafe>',entity:'US01',status:'Live',spend:1000000,transfer:1000000,cip:0}]);
  assert.match(html,/&lt;unsafe&gt;/);
  assert.doesNotMatch(html,/<unsafe>/);
});

test('factory utilization is capacity-weighted, not the average of site percentages',()=>{
  const rows=published.factory.filter(row=>row.month===published.meta.end_month);
  const expected=rows.reduce((sum,row)=>sum+Number(row.produced_units),0)/rows.reduce((sum,row)=>sum+Number(row.capacity_units),0);
  const html=visual.factories(rows);
  assert.ok(html.includes(`${(expected*100).toFixed(1)}%`));
  assert.match(html,/sum produced units \/ sum available capacity/);
  assert.doesNotMatch(html,/NaN|undefined/);
});
