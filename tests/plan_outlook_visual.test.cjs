const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
require('../web/plan-outlook-visual.js');
const visual=globalThis.FinancePlanOutlook;
const sum=(rows,key)=>rows.reduce((total,row)=>total+(Number(row[key])||0),0);

test('monthly Actual and frozen Budget chart reconciles to published YTD performance',()=>{
  const source=published.budget_performance,rows=visual.months(source);
  assert.equal(rows.length,new Set(source.map(row=>row.month)).size);
  for(const key of ['revenue','revenue_budget','ebit','ebit_budget'])assert.ok(Math.abs(sum(rows,key)-sum(source,key))<.01);
  for(const metric of ['revenue','ebit']){
    const html=visual.performance(source,metric);
    const delta=sum(source,metric)-sum(source,`${metric}_budget`);
    assert.equal((html.match(/data-po-ytd-month=/g)||[]).length,rows.length);
    assert.ok(html.includes(`${delta<0?'−':'+'}€${(Math.abs(delta)/1e6).toFixed(1)}m`));
    assert.doesNotMatch(html,/NaN|undefined/);
  }
});

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
  const {entity,division}=all[0];
  const one=all.filter(row=>row.entity===entity&&row.division===division);
  const html=visual.outlook(one,'ebit');
  const value=sum(one,'latest_fy_ebit');
  assert.ok(html.includes(`${value<0?'−':''}€${(Math.abs(value)/1e6).toFixed(1)}m`));
});

test('a revenue-free cost center opens EBIT instead of a zero-only visual',()=>{
  const center=published.fy_plan_bridge.find(row=>['fy_budget_revenue','fc_6_fy_revenue','fc_3_fy_revenue','fc_1_fy_revenue','latest_fy_revenue'].every(key=>Number(row[key])===0)&&Number(row.latest_fy_ebit)!==0);
  assert.ok(center);
  const match=row=>row.entity===center.entity&&row.division===center.division;
  const outlook=visual.outlook(published.fy_plan_bridge.filter(match),'revenue');
  const ytd=visual.performance(published.budget_performance.filter(match),'revenue');
  for(const html of [outlook,ytd]){
    assert.match(html,/cost center: no revenue/);
    assert.match(html,/data-po-(?:ytd-)?metric="revenue" aria-pressed="false" disabled/);
    assert.match(html,/data-po-(?:ytd-)?metric="ebit" aria-pressed="true"/);
  }
});
