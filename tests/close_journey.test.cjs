const {test}=require('node:test');
const assert=require('node:assert/strict');
global.FinanceReport={escape:value=>String(value)};
global.ReportContext={group:{key:'group',dimensions:[]}};
const journey=require('../web/close-journey.js');
const data=require('../web/data/dashboard.json');

test('close journey covers the complete process with real evidence routes',()=>{
  const validViews=new Set(['business-drivers','macro-sensitivities','data-journey','working-capital','operations-capex','fx','pnl','balance-sheet','intercompany','cash-flow','forecast','performance-review','action-execution','executive']);
  assert.equal(journey.stages.length,8);
  for(const stage of journey.stages){
    assert.equal(stage.controls.length,3,stage.title);
    assert.equal(stage.evidence.length,3,stage.title);
    assert.ok(stage.inputs.length>=3&&stage.outputs.length>=3,stage.title);
    assert.ok(stage.evidence.every(item=>validViews.has(item[1])),stage.title);
  }
});

test('every close-journey control exists and passes in the published close',()=>{
  for(const stage of journey.stages)for(const control of stage.controls){
    const [key,,source,limit,unit]=control;
    assert.ok(Object.hasOwn(data.validation,key),`${stage.title}: ${key}`);
    const value=data.validation[key];
    assert.equal(typeof value,'number',`${stage.title}: ${key}`);
    assert.ok(Number.isFinite(limit)&&limit>=0,`${stage.title}: ${key} has an explicit threshold`);
    assert.ok(['EUR','count'].includes(unit),`${stage.title}: ${key} has a declared unit`);
    assert.ok(source,`${stage.title}: ${key} has a source dataset`);
    assert.equal(journey.passed(data,control),true,`${stage.title}: ${key} = ${value} / ${limit}`);
    assert.match(journey.resultLabel(data,control),/\/.*(max|allowed)$/);
  }
  assert.equal(data.validation.passed,true);
});

test('close journey uses the exact published threshold instead of a generic finance tolerance',()=>{
  const creditLoss=journey.stages.find(stage=>stage.title==='Legal close').controls.find(control=>control[0]==='credit_loss_allowance_max_gap');
  assert.equal(creditLoss[3],0.05);
  assert.equal(journey.passed({validation:{credit_loss_allowance_max_gap:0.05}},creditLoss),true);
  assert.equal(journey.passed({validation:{credit_loss_allowance_max_gap:0.06}},creditLoss),false);
  assert.equal(journey.passed({validation:{credit_loss_allowance_max_gap:-0.06}},creditLoss),false);

  const strictCount=journey.stages.find(stage=>stage.title==='Actions & benefits').controls.find(control=>control[0]==='management_action_orphans');
  assert.equal(journey.passed({validation:{management_action_orphans:0}},strictCount),true);
  assert.equal(journey.passed({validation:{management_action_orphans:1}},strictCount),false);
  assert.equal(journey.passed({validation:{}},creditLoss),false);
});
