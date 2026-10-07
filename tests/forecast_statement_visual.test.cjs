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
  const base=rows.find(row=>row.scenario==='Base');
  assert.ok(html.includes(`€${(base.free_cash_flow_12m/1e6).toFixed(1)}m`));
  assert.doesNotMatch(html,/NaN|undefined/);
  assert.ok(Math.abs(base.ending_assets_12m-base.ending_liabilities_12m-base.ending_equity_12m)<.01);
});

test('scenario comparison switches to separately published 24-month flows and month-24 balances',()=>{
  const rows=['Downside','Base','Upside'].map((scenario,index)=>({
    scenario,revenue_12m:100+index,ebit_12m:10+index,free_cash_flow_12m:5+index,ending_cash_12m:40+index,
    ending_assets_12m:110,ending_liabilities_12m:50,ending_equity_12m:60,
    revenue_24m:250+index,ebit_24m:24+index,free_cash_flow_24m:17+index,ending_cash_24m:90+index,
    ending_assets_24m:160,ending_liabilities_24m:70,ending_equity_24m:90
  }));
  visual.setHorizon(24);
  const html=visual.scenarios(rows,'ebit');
  assert.match(html,/24 months/);
  assert.match(html,/Base P&amp;L · 24M flows/);
  assert.match(html,/€0\.0m · reconciled/);
  assert.ok(html.includes(`€${(rows[1].ebit_24m/1e6).toFixed(1)}m`));
  assert.ok(html.includes(`€${(rows[1].ending_cash_24m/1e6).toFixed(1)}m`));
  assert.doesNotMatch(html,/NaN|undefined/);
  visual.setHorizon(12);
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

test('workforce visual includes the complete published 24-month horizon when available',()=>{
  const rows=Array.from({length:24},(_,index)=>({scenario:'Base',vintage:'2026-09',horizon_month:index+1,month:`${index<12?'2026':'2027'}-${String(index%12+1).padStart(2,'0')}`,workforce_fte_forecast:100+index,workforce_target_fte:110+index,workforce_hires_forecast:2,personnel_cost_forecast:1000,non_people_opex_forecast:300}));
  const result=visual.workforceMonths(rows,'2026-09');
  assert.equal(result.length,24);
  assert.match(visual.workforce(result),/24 months · people/);
  assert.match(visual.workforce(result),/24M operating cost mix/);
});

test('paired workforce forecast is fixed group scope like integrated scenario summary',()=>{
  assert.equal(context.panel('forecast','Base workforce plan').key,'group');
  assert.equal(context.panel('forecast','Integrated three-statement scenarios').key,'group');
});
