const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const M=require('../web/report-model.js');
const row=(month,revenue,entity='US01',division='Software')=>({month,entity,division,revenue,marginal_contribution:revenue*.6,gross_profit:revenue*.4,opex:revenue*.1,depreciation:revenue*.05,ebit:revenue*.25,net_income:revenue*.2});
const ctx=vm.createContext({FinanceReport:M});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/report-charts.js'),'utf8'),ctx);
const C=ctx.ReportCharts;

test('presentation aggregation sums duplicate source lines, scopes and leaves inputs untouched',()=>{
  const rows=[row('2026-08',100),row('2026-08',50),row('2026-08',200,'DE01'),row('2026-08',300,'US01','Hardware')];
  const before=JSON.stringify(rows);
  assert.equal(M.aggregate(rows,{entity:'US01',division:'Software'})[0].revenue,150);
  assert.equal(M.aggregate(rows)[0].revenue,650);
  assert.equal(JSON.stringify(rows),before);
});
test('prior-year comparison matches the calendar month, not the row offset',()=>{
  const rows=[row('2025-08',100),row('2025-10',200),row('2026-08',120),row('2026-09',130)];
  const values=M.comparisons(rows,'revenue','2026-09');
  assert.equal(values.at(-2).prior,100);
  assert.equal(values.at(-1).prior,null);
  assert.equal(M.priorMonth('2026-01'),'2025-01');
});
test('missing and nonfinite measures remain unavailable rather than zero',()=>{
  assert.equal(M.aggregate([{...row('2026-08',100),ebit:null}])[0].ebit,null);
  assert.equal(M.aggregate([{...row('2026-08',100),ebit:NaN}])[0].ebit,null);
  assert.deepEqual(M.variance(null,100),{delta:null,relative:null,favorable:null});
  assert.equal(C.money(null),'—');
  assert.equal(M.variance(10,0).relative,null);
});
test('variance polarity handles costs, losses and neutral differences explicitly',()=>{
  assert.equal(M.variance(110,100).favorable,true);
  assert.equal(M.variance(110,100,-1).favorable,false);
  assert.equal(M.variance(90,100,-1).favorable,true);
  assert.equal(M.variance(-80,-100).relative,.2);
  assert.equal(M.variance(10,10).favorable,null);
});
test('bridge steps reconcile naturally to each reported subtotal without a plug',()=>{
  const steps=M.bridge(row('2026-08',100));
  assert.equal(steps[1].end,steps[2].end);
  assert.equal(steps[3].end,steps[4].end);
  assert.equal(steps[6].end,steps[7].end);
  assert.equal(steps.at(-1).end,25);
  assert.deepEqual(steps.filter(s=>s.total).map(s=>s.start),[0,0,0,0]);
});
test('pagination covers every row exactly once and clamps invalid page indexes',()=>{
  const rows=Array.from({length:103},(_,i)=>i),found=[];
  for(let i=0;i<11;i++)found.push(...M.page(rows,i,10).items);
  assert.deepEqual(found,rows);
  assert.equal(M.page(rows,999,10).index,10);
  assert.equal(M.page([],0,0).count,1);
});
test('chart text is escaped and SVG bars use a real signed baseline',()=>{
  const html=C.series([{month:'2026-07',value:100},{month:'2026-08',value:-100}],'value','month','2026-08');
  assert.match(html,/y1="147.5"/);
  assert.match(html,/y="147.5" width="32" height="117.5"/);
  const escaped=C.trend([{month:'<script>',actual:1,prior:0}],'Revenue');
  assert.ok(!escaped.includes('<script>'));
  assert.match(escaped,/&lt;script&gt;/);
});
test('actual plan and forecast use solid outlined and hatched notation; FTE is not currency',()=>{
  assert.match(C.series([{month:'2026-08',revenue_budget:100}],'revenue_budget','month','2026-08'),/fill="white"/);
  assert.match(C.series([{month:'2026-09',ending_cash:100}],'ending_cash','month','2026-08'),/fill="url\(#forecast-hatch-/);
  const fte=C.series([{month:'2026-08',ending_fte:123}],'ending_fte','month','2026-08');
  assert.match(fte,/123 FTE/);
  assert.ok(!fte.includes('EUR'));
});
test('published management data reconciles the presentation bridge for every entity/division',()=>{
  const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../web/data/dashboard.json'),'utf8'));
  for(const entity of ['all',...new Set(data.management_detail.map(r=>r.entity))]){
    for(const division of ['all',...new Set(data.management_detail.map(r=>r.division))]){
      const actual=M.aggregate(data.management_detail,{entity,division}).find(r=>r.month===data.meta.end_month);
      if(!actual)continue;
      const bridge=M.bridge(actual);
      assert.ok(Math.abs(bridge[6].end-bridge[7].end)<=.02,`${entity}/${division}`);
    }
  }
});
