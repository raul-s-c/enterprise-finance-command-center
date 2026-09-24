const test=require('node:test');
const assert=require('node:assert/strict');
require('../web/lifecycle-story-visual.js');
const visual=globalThis.FinanceLifecycleVisual;

test('one monthly snapshot never becomes an invented trend',()=>{
  const actions=[{status:'Open'},{status:'Closed'}],history=[{month:'2026-08',active:1,closed:1}];
  const html=visual.status(actions,history,'<table id="history"></table>');
  assert.match(html,/First controlled snapshot; a trend requires a second close/);
  assert.match(html,/1 Open, 1 Closed/);
  assert.match(html,/id="history"/);
  assert.doesNotMatch(html,/plv-history-bars/);
});

test('later snapshots are charted from source values, including negative state changes',()=>{
  const actions=[{status:'Open'},{status:'Closed'},{status:'Cancelled'}];
  const history=[{month:'2026-08',active:2,closed:0},{month:'2026-09',active:1,closed:1}];
  const html=visual.status(actions,history,'<table></table>');
  assert.match(html,/plv-history-bars/);
  assert.match(html,/2026-09, 1 active and 1 closed/);
  assert.match(html,/1 Cancelled/);
});

test('zero overdue is distinct from the next due open actions',()=>{
  const actions=[{action_id:'A1',status:'Open',priority:'P1',trigger_metric:'<OPEX>',owner_role:'CFO',due_month:'2026-09',action:'Control cost',review_id:'REV-1',source_dataset:'budget.csv'}];
  const html=visual.due(actions,[],'2026-08','<table id="late"></table>');
  assert.match(html,/No overdue actions at the 2026-08 close/);
  assert.match(html,/Next due actions/);
  assert.match(html,/&lt;OPEX&gt;/);
  assert.match(html,/id="late"/);
});
