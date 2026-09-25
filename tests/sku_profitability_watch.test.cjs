const {test}=require('node:test');
const assert=require('node:assert/strict');
const data=require('../web/data/dashboard.json');
require('../web/sku-profitability-watch.js');

test('SKU cost bridges disclose source rounding without a balancing adjustment',()=>{
  const rows=data.product_profitability;
  assert.equal(rows.length,220);
  const residuals=rows.map(globalThis.SkuProfitabilityWatch.residuals);
  assert.ok(residuals.some(row=>Math.abs(row.mc)>.01),'MC source rounding must remain visible');
  assert.ok(residuals.some(row=>Math.abs(row.gp)>.01),'GP source rounding must remain visible');
  assert.ok(residuals.every(row=>Math.abs(row.mc)<1&&Math.abs(row.gp)<1&&Math.abs(row.op)<.01));
  assert.equal(rows.filter(row=>row.operating_contribution<0).length,0);
});
