const {test}=require('node:test');
const assert=require('node:assert/strict');
const visual=require('../web/opex-composition-visual.js');
const published=require('../web/data/dashboard.json');

test('group OPEX uses actual, workforce and independently reconciled division sources',()=>{
  const row=visual.model(published).at(-1);
  const actual=published.actual.find(item=>item.month===published.meta.end_month);
  const workforce=published.workforce_summary.find(item=>item.month===published.meta.end_month);
  assert.equal(row.opex,actual.opex);
  assert.equal(row.personnel,workforce.personnel_cost);
  assert.ok(Math.abs(row.nonPeople-(row.opex-row.personnel))<.005);
  assert.equal(row.byDivision.length,4);
  assert.ok(Math.abs(row.divisionGap)<=.05);
  const html=visual.visual(published);
  assert.match(html,/Division source total − group OPEX: €0\.00 · reconciled/);
  assert.equal((html.match(/data-ox-month=/g)||[]).length,12);
  assert.match(html,/management_detail\.opex/);
  assert.match(html,/not an invoice allocation/);
});

test('missing or duplicate workforce never creates an invented personnel split',()=>{
  const source={meta:{end_month:'2026-08'},actual:[{month:'2026-08',opex:100}],
    workforce_summary:[{month:'2026-08',personnel_cost:70},{month:'2026-08',personnel_cost:60}],
    management_detail:[{month:'2026-08',division:'Software',opex:100}]};
  const row=visual.model(source)[0];
  assert.equal(row.personnel,null);
  assert.equal(row.nonPeople,null);
  assert.match(visual.visual(source),/no balancing allocation is shown/);
});

test('negative non-people difference is exposed, never clamped to zero',()=>{
  const source={meta:{end_month:'2026-08'},actual:[{month:'2026-08',opex:100}],
    workforce_summary:[{month:'2026-08',personnel_cost:120}],
    management_detail:[{month:'2026-08',division:'Software',opex:100}]};
  assert.equal(visual.model(source)[0].nonPeople,-20);
  const html=visual.visual(source);
  assert.match(html,/no balancing allocation is shown/);
  assert.match(html,/−€20\.00/);
});
