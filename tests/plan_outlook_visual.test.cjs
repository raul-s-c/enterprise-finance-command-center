const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
require('../web/plan-outlook-visual.js');
const visual=globalThis.FinancePlanOutlook;
const sum=(rows,key)=>rows.reduce((total,row)=>total+(Number(row[key])||0),0);

test('outlook shows all five published full-year revenue vintages without additive allocations',()=>{
  const rows=published.fy_plan_bridge;
  const html=visual.outlook(rows,'revenue');
  assert.equal((html.match(/class="po-row /g)||[]).length,5);
  for(const label of ['FY Budget','FC-6','FC-3','FC-1','Latest FY'])assert.ok(html.includes(label));
  for(const key of ['fy_budget_revenue','fc_6_fy_revenue','fc_3_fy_revenue','fc_1_fy_revenue','latest_fy_revenue'])assert.ok(html.includes(`€${(Math.abs(sum(rows,key))/1e6).toFixed(1)}m`));
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('EBIT view preserves negative source values and the latest-versus-budget calculation',()=>{
  const rows=published.fy_plan_bridge;
  const html=visual.outlook(rows,'ebit');
  const delta=sum(rows,'latest_fy_ebit')-sum(rows,'fy_budget_ebit');
  assert.ok(html.includes(`${delta<0?'−':'+'}€${(Math.abs(delta)/1e6).toFixed(1)}m`));
  assert.match(html,/data-po-metric="ebit" aria-pressed="true"/);
  assert.match(html,/Bars compare published full-year totals, not additive changes/);
});

test('scope is applied to source rows before charting',()=>{
  const all=published.fy_plan_bridge;
  const one=all.filter(row=>row.entity==='CN01'&&row.division==='Hardware');
  const html=visual.outlook(one,'ebit');
  assert.ok(html.includes(`−€${(Math.abs(sum(one,'latest_fy_ebit'))/1e6).toFixed(1)}m`));
});
