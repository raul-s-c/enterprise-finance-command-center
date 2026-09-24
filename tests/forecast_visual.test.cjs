const {test}=require('node:test');
const assert=require('node:assert/strict');
const data=require('../web/data/dashboard.json');
require('../web/forecast-visual.js');

test('forecast charts preserve all published horizons and financial sign semantics',()=>{
  const html=global.FinanceForecastVisual.accuracy(data.forecast_accuracy);
  assert.equal((html.match(/class="fv-error-point"/g)||[]).length,18);
  assert.equal((html.match(/class="fv-negative"/g)||[]).length,15);
  assert.match(html,/10\.1%/);
  assert.match(html,/0\.5% at 1M/);
  assert.match(html,/-5\.8% at 18M/);
  assert.match(html,/negative means under-forecast/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('liquidity bars use reported OCF, CAPEX and ending cash without inventing a reconciliation',()=>{
  const html=global.FinanceForecastVisual.liquidity(data.liquidity_forecast_summary);
  assert.equal((html.match(/class="fv-scenario"/g)||[]).length,3);
  for(const amount of ['€78.8M','€72.0M','€83.4M','€1.6M','€262.6M'])assert.ok(html.includes(amount),amount);
  assert.match(html,/not a cash reconciliation/);
  assert.doesNotMatch(html,/NaN|undefined/);
  assert.match(global.FinanceForecastVisual.accuracy([{horizon_month:1,mape:null,bias:0}]),/No realized forecast vintages/);
  assert.match(global.FinanceForecastVisual.liquidity([{scenario:'<unsafe>',forecast_operating_cash_flow_12m:1e6,forecast_capex_12m:1e5,ending_cash_12m:2e6}]),/&lt;unsafe&gt;/);
});
