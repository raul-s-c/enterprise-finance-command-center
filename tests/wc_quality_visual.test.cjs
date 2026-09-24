const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
require('../web/wc-quality-visual.js');
const visual=globalThis.FinanceWCQualityVisual;

test('AR and inventory buckets reconcile to the published gross balances',()=>{
  for(const [summary,fields,total,risk] of [
    [published.ar_aging_summary.at(-1),[['Current','current'],['1–30','overdue_1_30'],['31–60','overdue_31_60'],['61–90','overdue_61_90'],['>90','overdue_90_plus']],'total_ar','overdue_ar'],
    [published.inventory_aging_summary.at(-1),[['0–30','age_0_30'],['31–60','age_31_60'],['61–90','age_61_90'],['91–180','age_91_180'],['>180','age_180_plus']],'inventory_value','obsolescence_risk_value']
  ]){
    const sum=fields.reduce((value,[,key])=>value+Number(summary[key]),0);
    assert.ok(Math.abs(sum-Number(summary[total]))<.05);
    const html=visual.aging(summary,fields,{title:'Source schedule',totalKey:total,riskKey:risk,riskLabel:'Risk'});
    assert.equal((html.match(/class="wq-bucket-/g)||[]).length,5);
    assert.match(html,/Buckets reconcile to the published gross balance/);
    assert.doesNotMatch(html,/NaN|undefined/);
  }
});

test('reserve ranks use actual positive source records and escape labels',()=>{
  const rows=[{customer_name:'<unsafe>',entity:'DE01',division:'Hardware',credit_loss_allowance:200,gross_ar:1000},{customer_name:'Small',entity:'US01',division:'Software',credit_loss_allowance:50,gross_ar:500},{customer_name:'Zero',credit_loss_allowance:0,gross_ar:300}];
  const html=visual.ranked(rows,{label:row=>row.customer_name,amount:'credit_loss_allowance',gross:'gross_ar',description:'allowances'});
  assert.equal((html.match(/class="wq-rank"/g)||[]).length,2);
  assert.ok(html.indexOf('&lt;unsafe&gt;')<html.indexOf('Small'));
  assert.match(html,/€200/);
  assert.match(html,/€1.0k gross · 20.0%/);
  assert.doesNotMatch(html,/<unsafe>|Zero/);
  assert.match(visual.ranked([],{label:row=>row.name,amount:'reserve',gross:'gross',description:'none'}),/No positive reserves/);
});

test('ranked source totals reconcile to the published group allowances',()=>{
  const month=published.meta.end_month,summary=published.provision_summary.at(-1);
  for(const [detail,key] of [[published.credit_loss_detail,'credit_loss_allowance'],[published.inventory_provision_detail,'inventory_provision']]){
    const total=detail.filter(row=>row.month===month).reduce((sum,row)=>sum+Number(row[key]||0),0);
    assert.ok(Math.abs(total-Number(summary[key]))<.01,`${key} differs from published provision summary`);
  }
});
