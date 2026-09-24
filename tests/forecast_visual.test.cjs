const {test}=require('node:test');
const assert=require('node:assert/strict');
const data=require('../web/data/dashboard.json');
require('../web/forecast-visual.js');

test('forecast charts preserve all published horizons and financial sign semantics',()=>{
  const html=global.FinanceForecastVisual.accuracy(data.forecast_accuracy);
  assert.equal((html.match(/class="fv-error-point"/g)||[]).length,18);
  assert.equal((html.match(/class="fv-negative"/g)||[]).length,data.forecast_accuracy.filter(row=>Number(row.bias)<0).length);
  const pct=value=>new Intl.NumberFormat('en-GB',{style:'percent',minimumFractionDigits:1,maximumFractionDigits:1}).format(Number(value));
  const first=data.forecast_accuracy[0],last=data.forecast_accuracy.at(-1);
  assert.match(html,new RegExp(pct(first.mape).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  assert.ok(html.includes(`${Number(first.bias)>0?'+':''}${pct(first.bias)} at ${first.horizon_month}M`));
  assert.ok(html.includes(`${Number(last.bias)>0?'+':''}${pct(last.bias)} at ${last.horizon_month}M`));
  assert.match(html,/negative means under-forecast/);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('liquidity bars use reported OCF, CAPEX and ending cash without inventing a reconciliation',()=>{
  const html=global.FinanceForecastVisual.liquidity(data.liquidity_forecast_summary);
  assert.equal((html.match(/class="fv-scenario"/g)||[]).length,3);
  const money=value=>`€${(Number(value)/1e6).toFixed(1)}M`;
  for(const row of data.liquidity_forecast_summary){
    for(const key of ['forecast_operating_cash_flow_12m','forecast_capex_12m','ending_cash_12m'])assert.ok(html.includes(money(row[key])),`${row.scenario} ${key}`);
  }
  assert.match(html,/not a cash reconciliation/);
  assert.doesNotMatch(html,/NaN|undefined/);
  assert.match(global.FinanceForecastVisual.accuracy([{horizon_month:1,mape:null,bias:0}]),/No realized forecast vintages/);
  assert.match(global.FinanceForecastVisual.liquidity([{scenario:'<unsafe>',forecast_operating_cash_flow_12m:1e6,forecast_capex_12m:1e5,ending_cash_12m:2e6}]),/&lt;unsafe&gt;/);
});
