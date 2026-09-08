const {test}=require('node:test');
const assert=require('node:assert/strict');
const C=require('../web/contribution-explorer.js');
const data=require('../web/data/dashboard.json');
test('signed contributions reconcile without hiding losses or undefined shares',()=>{
  const r=C.aggregate([{entity:'A',v:10},{entity:'B',v:-10},{entity:'C',v:null}],'v','entity');
  assert.equal(r.total,0);assert.equal(r.missing,1);assert.equal(r.groups.length,2);assert.ok(r.groups.every(g=>g.share===null));
  assert.equal(C.aggregate([{v:3}],'v','entity').groups[0].name,'Unattributed');
});
test('CAPEX separates cash spending from noncash asset transfers',()=>{
  const month=data.capex.find(r=>r.event==='GO_LIVE').month;
  assert.ok(C.records(data,'capex',month,'GO_LIVE').every(r=>r.event==='GO_LIVE'));
  assert.ok(C.records(data,'capex',month,'SPEND').every(r=>r.event==='SPEND'));
});
test('every dimension and measure reconciles to its own source, without changing data',()=>{
  const before=JSON.stringify(data);
  for(const [key,def]of Object.entries(C.definitions)){
    const months=[...new Set(data[def.source].map(r=>r.month||data.meta.end_month))];
    for(const month of months)for(const event of key==='capex'?['SPEND','GO_LIVE']:['SPEND']){
      const rows=C.records(data,key,month,event);
      for(const metric of def.metrics)for(const dimension of def.dimensions){
        assert.ok(rows.every(r=>typeof r[metric]==='number'),`${key}:${metric}`);
        assert.ok(rows.every(r=>r[dimension]),`${key}:${dimension}`);
        const result=C.aggregate(rows,metric,dimension),total=rows.reduce((n,r)=>n+r[metric],0);
        assert.ok(Math.abs(total-result.total)<0.00001,`${key}:${month}:${metric}:${dimension}`);
      }
    }
  }
  assert.equal(JSON.stringify(data),before);
});
test('legacy coverage and unavailable product/entity attribution are explicit',()=>{
  for(const key of ['ar','inventory'])assert.match(C.definitions[key].note,/watchlist only/);
  assert.ok(!C.definitions.products.dimensions.includes('entity'));
  assert.match(C.definitions.products.period,/Trailing 12/);
});
test('complete working-capital sources expose gross-to-net measures and deeper dimensions',()=>{
  const enhanced={
    credit_loss_detail:[{entity:'US01',division:'Software',customer_segment:'Core',customer:'C1',gross_ar:100,credit_loss_allowance:4,net_ar:96,overdue_ar:20,current:80,overdue_1_30:20,overdue_31_60:0,overdue_61_90:0,overdue_90_plus:0}],
    inventory_provision_detail:[{entity:'CZ01',division:'Hardware',product_family:'Devices',product_subfamily:'Edge',product_type:'Terminal',quality_tier:'Premium',generation:'Current',product:'HW-1',gross_inventory:80,inventory_provision:5,net_inventory:75,slow_moving_value:10,obsolescence_risk_value:2,age_0_30:50,age_31_60:20,age_61_90:10,age_91_180:0,age_180_plus:0}],
  };
  assert.equal(C.source(enhanced,'ar'),'credit_loss_detail');
  assert.ok(C.metrics(enhanced,'ar').includes('net_ar'));
  assert.ok(C.dimensions(enhanced,'ar').includes('customer_segment'));
  assert.match(C.note(enhanced,'ar'),/Complete external customer schedule/);
  assert.equal(C.source(enhanced,'inventory'),'inventory_provision_detail');
  assert.ok(C.metrics(enhanced,'inventory').includes('inventory_provision'));
  assert.ok(C.dimensions(enhanced,'inventory').includes('product_subfamily'));
});
test('enhanced product lineage activates only when entity-product records are published',()=>{
  const enhanced={entity_product_profitability:[{entity:'US01',division:'Hardware',product_family:'Devices',product_subfamily:'Edge',product_type:'Terminal',quality_tier:'Premium',product:'HW-1',revenue:100,variable_production_cost:45,variable_selling_cost:5,fixed_production_cost:10,marginal_contribution:50,gross_profit:40,opex:8,operating_contribution:32}]};
  assert.equal(C.source(enhanced,'products'),'entity_product_profitability');
  assert.deepEqual(C.dimensions(enhanced,'products'),['entity','division','product_family','product_subfamily','product_type','quality_tier','product']);
  assert.ok(C.metrics(enhanced,'products').includes('variable_production_cost'));
  assert.equal(C.records(enhanced,'products','2026-08').length,1);
  assert.equal(C.source(data,'products'),'product_profitability');
});
