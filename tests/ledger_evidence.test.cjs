const {test}=require('node:test');
const assert=require('node:assert/strict');
const C=require('../web/contribution-explorer.js');
test('ledger evidence discloses legal scope without inventing customer settlement links',()=>{
  const postings=[{month:'2026-08',entity:'US01',division:'Hardware',account:'1100_AR',journal_id:'A'},{month:'2026-08',entity:'ES01',division:'Hardware',account:'1100_AR',journal_id:'B'},{month:'2026-08',entity:'US01',division:'Hardware',account:'2100_AP',journal_id:'C'}];
  const data={working_capital_postings:postings,working_capital_rollforward:postings};
  const result=C.ledgerEvidence(data,[{entity:'US01',division:'Hardware',component:'Receivables',customer:'X'}],'2026-08');
  assert.deepEqual(result.postings.map(r=>r.journal_id),['A']);
  assert.equal(result.scope.customer,undefined);
  assert.equal(C.ledgerEvidence(data,[{entity:'CONSOLIDATION'}],'2026-08').postings.length,0);
  assert.equal(C.ledgerEvidence({},[],'2026-08').balances.length,0);
  assert.equal(C.ledgerEvidence(data,[],'2026-08').postings.length,0);
});
test('the integrated NWC bridge only offers its reconciled NWC measure',()=>{
  assert.deepEqual(C.metrics({credit_loss_detail:[{month:'2026-08',gross_ar:100,credit_loss_allowance:5,net_ar:95}]},'nwc'),['net_working_capital']);
});
