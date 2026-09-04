const test=require('node:test');
const assert=require('node:assert/strict');
const context=require('../web/report-context.js');
const data=require('../web/data/dashboard.json');
const model=require('../web/report-model.js');

test('group-only pages do not advertise nonfunctional dimensions',()=>{
  for(const title of ['Base forecast Balance Sheet','Funding structure','Group covenant sensitivity','CAPEX portfolio','Close-month macro observations']){
    const policy=context.panel('balance-sheet',title);
    assert.deepEqual(policy.dimensions,[]);
    const result=context.resolve(data,policy,{entity:'US01',division:'Software'});
    assert.deepEqual(result.options,{entity:[],division:[]});
    assert.deepEqual(result.scope,{entity:'US01',division:'Software'});
  }
});

test('operating filter choices exclude unsupported entity/division combinations, but retain losses and valid zeros',()=>{
  const policy=context.panel('executive','Overview');
  const fixture={meta:{end_month:'2026-08'},management_detail:[
    {month:'2026-08',entity:'US01',division:'Software',revenue:100,ebit:0},
    {month:'2026-08',entity:'CZ01',division:'Hardware',revenue:0,opex:5,ebit:-5},
    {month:'2026-08',entity:'CZ01',division:'Software',revenue:0,opex:0,ebit:0},
  ]};
  const result=context.resolve(fixture,policy,{entity:'all',division:'Software'});
  assert.deepEqual(result.options.entity,['US01']);
  const hardware=context.resolve(fixture,policy,{entity:'CZ01',division:'all'});
  assert.deepEqual(hardware.options.division,['Hardware']);
  const invalid=context.resolve(fixture,policy,{entity:'CZ01',division:'Software'});
  assert.deepEqual(invalid.scope,{entity:'all',division:'Software'});
  assert.deepEqual(invalid.adjusted,['entity']);
});

test('all offered choices have real records in the exact applicable scope',()=>{
  const policies=[...new Set([...Object.values(context.panels),...['Revenue','ARR','Ending FTE','Current customer advances','Approved plans','Open FX documents'].map(context.card)])];
  for(const policy of policies){
    for(const entity of ['all',...new Set(data.management_detail.map(r=>r.entity))]){
      for(const division of ['all',...new Set(data.management_detail.map(r=>r.division))]){
        const result=context.resolve(data,policy,{entity,division});
        const records=context.rows(data,policy);
        for(const dimension of policy.dimensions)for(const value of result.options[dimension])assert.ok(records.some(row=>context.matches(row,{...result.scope,[dimension]:value},policy)),`${policy.key}/${dimension}/${value}`);
        if(result.empty)assert.ok(result.options.entity.length===0&&result.options.division.length===0);
      }
    }
  }
});

test('Software and factory pages only expose their own entity domain',()=>{
  const software=context.resolve(data,context.card('ARR'),{entity:'all',division:'Hardware'});
  assert.ok(!software.options.entity.includes('CN01'));
  assert.deepEqual(software.options.division,[]);
  const factory=context.resolve(data,context.card('Factory utilization'),{entity:'all',division:'Software'});
  assert.deepEqual(factory.options.entity,['CN01','CZ01']);
});

test('table sorting compares compact currency, negatives, percentages and numeric identifiers',()=>{
  assert.ok(model.compareDisplay('€900K','€2M',true)<0);
  assert.ok(model.compareDisplay('-€2M','€0',true)<0);
  assert.ok(model.compareDisplay('(€2M)','€0',true)<0);
  assert.ok(model.compareDisplay('2.5%','12%',true)<0);
  assert.ok(model.compareDisplay('—','0',true)>0);
  assert.ok(model.compareDisplay('SKU 9','SKU 10')<0);
});
