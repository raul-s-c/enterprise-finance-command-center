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
  for(const stage of journey.stages)for(const [key] of stage.controls){
    assert.ok(Object.hasOwn(data.validation,key),`${stage.title}: ${key}`);
    const value=data.validation[key];
    assert.equal(typeof value,'number',`${stage.title}: ${key}`);
    assert.ok(Math.abs(value)<0.1,`${stage.title}: ${key} = ${value}`);
  }
  assert.equal(data.validation.passed,true);
});
