const {test}=require('node:test');
const assert=require('node:assert/strict');
const navigation=require('../web/report-navigation.js');

const expected=[
  'executive','pnl','margin','profitability','working-capital','cash-flow','treasury','balance-sheet',
  'forecast','macro-sensitivities','business-drivers','intercompany','operations-capex','fx',
  'close-journey','performance-review','action-execution','data-journey'
];

test('six decision areas replace the eighteen-item primary navigation',()=>{
  assert.equal(navigation.areas.length,6);
  const routed=navigation.areas.flatMap(area=>area.views);
  assert.deepEqual([...routed].sort(),[...expected].sort());
  assert.equal(new Set(routed).size,expected.length);
  for(const area of navigation.areas){
    assert.ok(area.views.includes(area.landing),area.id);
    assert.ok(area.views.length<=4,area.id);
  }
});

test('direct report routes resolve to their decision area',()=>{
  assert.equal(navigation.areaFor('pnl').label,'Performance');
  assert.equal(navigation.areaFor('treasury').label,'Cash & Balance');
  assert.equal(navigation.areaFor('macro-sensitivities').label,'Plan & Outlook');
  assert.equal(navigation.areaFor('fx').label,'Operations');
  assert.equal(navigation.areaFor('action-execution').label,'Close & Controls');
});
