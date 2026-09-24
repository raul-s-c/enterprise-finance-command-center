const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
const context=require('../web/report-context.js');
require('../web/factory-absorption-visual.js');
const visual=globalThis.FinanceFactoryVisual;

test('factory actual less absorbed cost reconciles to posted gross-profit variance',()=>{
  const current=published.hardware_factory_economics.filter(row=>row.month===published.meta.end_month);
  assert.equal(current.length,2);
  for(const row of current)assert.ok(Math.abs(row.actual_fixed_factory_cost-row.absorbed_fixed_cost-row.absorption_variance)<.01);
  const html=visual.factory(current);
  assert.match(html,/reconciled/);
  assert.match(html,/Under-absorption/);
  assert.match(html,/Brno Smart Manufacturing/);
  assert.match(html,/Suzhou Manufacturing Hub/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('mix is source-factory sales units, not monthly production units',()=>{
  const mix=published.hardware_mix.filter(row=>row.month===published.meta.end_month);
  const produced=published.hardware_factory_economics.filter(row=>row.month===published.meta.end_month).reduce((sum,row)=>sum+row.produced_units,0);
  const sales=mix.reduce((sum,row)=>sum+row.units,0);
  assert.notEqual(sales,produced);
  const html=visual.mix(mix);
  assert.match(html,/Sales mix is not current-month factory output/);
  assert.match(html,/704/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('factory pair is fixed Group scope to match both source visuals',()=>{
  assert.equal(context.panel('business-drivers','Factory absorption accounting').key,'group');
  assert.equal(context.panel('business-drivers','Production mix').key,'group');
});
