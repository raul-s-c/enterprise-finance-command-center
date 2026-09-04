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
test('partial WC coverage and unavailable product/entity attribution are explicit',()=>{
  for(const key of ['ar','inventory','ap'])assert.match(C.definitions[key].note,/watchlist only/);
  assert.ok(!C.definitions.products.dimensions.includes('entity'));
  assert.match(C.definitions.products.period,/Trailing 12/);
});
