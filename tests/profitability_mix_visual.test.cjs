const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
const context=require('../web/report-context.js');
require('../web/profitability-mix-visual.js');
const visual=globalThis.FinanceProfitabilityMix;

test('family and tier cuts reconcile for revenue and operating contribution',()=>{
  for(const measure of ['revenue','operating_contribution']){
    const families=published.product_family_profitability.reduce((sum,row)=>sum+Number(row[measure]),0);
    const tiers=published.quality_tier_profitability.reduce((sum,row)=>sum+Number(row[measure]),0);
    assert.ok(Math.abs(families-tiers)<.01,`${measure} difference ${families-tiers}`);
  }
  assert.match(visual.tiers(published.quality_tier_profitability,published.product_family_profitability),/reconciled/);
  const remaining=published.product_family_profitability.length-6;
  if(remaining>0)assert.ok(visual.family(published.product_family_profitability).includes(`Other ${remaining} families`));
});

test('profitability panels offer only supported division filters',()=>{
  const family=context.panel('profitability','Family economics');
  const tiers=context.panel('profitability','Quality-tier economics');
  assert.deepEqual(family.dimensions,['division']);
  assert.deepEqual(tiers.dimensions,['division']);
  for(const division of ['Hardware','Software','Events','Spare Parts']){
    const f=visual.selected(published.product_family_profitability,division);
    const t=visual.selected(published.quality_tier_profitability,division);
    assert.ok(f.length&&t.length);
    assert.ok(Math.abs(f.reduce((sum,row)=>sum+row.revenue,0)-t.reduce((sum,row)=>sum+row.revenue,0))<.01);
  }
});

test('family names are escaped in the visual',()=>{
  const html=visual.family([{division:'<unsafe>',product_family:'& family',revenue:1000000,operating_contribution:1,gross_margin_pct:.3}]);
  assert.match(html,/&lt;unsafe&gt;/);
  assert.match(html,/&amp; family/);
  assert.doesNotMatch(html,/<unsafe>/);
});
