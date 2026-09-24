const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
const context=require('../web/report-context.js');
require('../web/forecast-statement-visual.js');
const visual=globalThis.FinanceForecastStory;

test('scenario comparison uses the three published cases and the actual balance identity',()=>{
  const rows=published.three_statement_forecast_summary;
  const html=visual.scenarios(rows,'free_cash_flow_12m');
  assert.equal((html.match(/class="fs-scenario /g)||[]).length,3);
  assert.match(html,/Free cash flow/);
  assert.match(html,/Balance check €0.0m · reconciled/);
  assert.match(html,/€78.0m/);
  assert.doesNotMatch(html,/NaN|undefined/);
  const base=rows.find(row=>row.scenario==='Base');
  assert.ok(Math.abs(base.ending_assets_12m-base.ending_liabilities_12m-base.ending_equity_12m)<.01);
});

test('scenario names are escaped and no invented case is displayed',()=>{
  const html=visual.scenarios([{scenario:'Base',revenue_12m:1,ebit_12m:1,free_cash_flow_12m:1,ending_cash_12m:1,ending_assets_12m:1,ending_liabilities_12m:0,ending_equity_12m:1},{scenario:'<unsafe>'}]);
  assert.doesNotMatch(html,/<unsafe>/);
  assert.equal((html.match(/class="fs-scenario /g)||[]).length,1);
});

test('group Base workforce aggregation reconciles personnel and non-people OPEX',()=>{
  const rows=visual.workforceMonths(published.workforce_forecast,published.meta.end_month);
  assert.equal(rows.length,12);
  for(const row of rows)assert.ok(Math.abs(row.personnel+row.nonPeople-row.opex)<.1,`OPEX split failed for ${row.month}`);
  assert.ok(rows.at(-1).fte>0);
  assert.match(visual.workforce(rows),/Forecast FTE vs target/);
  assert.match(visual.workforce(rows),/Across all entities/);
  assert.doesNotMatch(visual.workforce(rows),/NaN|undefined/);
});

test('paired workforce forecast is fixed group scope like integrated scenario summary',()=>{
  assert.equal(context.panel('forecast','Base workforce plan').key,'group');
  assert.equal(context.panel('forecast','Integrated three-statement scenarios').key,'group');
});
