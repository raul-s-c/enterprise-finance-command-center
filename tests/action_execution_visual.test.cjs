const test=require('node:test');
const assert=require('node:assert/strict');
require('../web/action-execution-visual.js');
const visual=globalThis.FinanceActionVisual;

test('portfolio stage counts use published statuses, not invented progress',()=>{
  const rows=[
    {priority:'P1',execution_status:'Approved',intervention_type:'Pricing',primary_driver:'Price',owner_role:'CFO',effective_month:'2026-09',expected_outcome:'<script>alert(1)</script>',execution_evidence:'Approved plan',source_review_id:'REV-1',expected_benefit_eur:100},
    {priority:'P2',execution_status:'Benefits tracking',intervention_type:'Cost',primary_driver:'OPEX',owner_role:'Controller',effective_month:'2026-10',expected_outcome:'Cost recovery',execution_evidence:'Source control',source_review_id:'REV-2',expected_benefit_eur:200},
    {priority:'P3',execution_status:'Cancelled',intervention_type:'Withdrawn',primary_driver:'None',owner_role:'CFO',effective_month:'2026-11',expected_outcome:'No change',execution_evidence:'Cancellation log',source_review_id:'REV-3',expected_benefit_eur:0}
  ];
  const html=visual.portfolio(rows,'<table></table>');
  assert.match(html,/Approved<\/span>[\s\S]*?<strong>1<\/strong>/);
  assert.match(html,/Benefits tracking<\/span>[\s\S]*?<strong>1<\/strong>/);
  assert.match(html,/Cancelled<\/span>[\s\S]*?<strong>1<\/strong>/);
  assert.match(html,/View all 3 approved plans/);
  assert.match(html,/&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html,/<script>alert\(1\)<\/script>/);
});

test('forecast bridge preserves signed month values and source table',()=>{
  const rows=[{month:'2026-09',action_ebit_impact:-1250,action_revenue_impact:500,active_action_count:2},{month:'2026-10',action_ebit_impact:3000,action_revenue_impact:900,active_action_count:3}];
  const html=visual.bridge(rows,'<table id="source"></table>');
  assert.match(html,/aev-bar-negative/);
  assert.match(html,/-€1,250/);
  assert.match(html,/data-aev-month="2026-10"/);
  assert.match(html,/complete 2-month additive bridge/);
  assert.match(html,/id="source"/);
});

test('actual impact distinguishes pre-effective zero from later signed activity',()=>{
  const plan=[{effective_month:'2026-09'}],zero=visual.actual([{month:'2026-08',action_ebit_impact:0}],plan,'2026-08','<table></table>');
  assert.match(zero,/all zero before effective dates/);
  assert.match(zero,/2026-09/);
  const active=visual.actual([{month:'2026-09',action_ebit_impact:-100}],plan,'2026-09','<table></table>');
  assert.match(active,/aev-actual-bars/);
  assert.match(active,/aev-bar-negative/);
  assert.doesNotMatch(active,/all zero before effective dates/);
});
