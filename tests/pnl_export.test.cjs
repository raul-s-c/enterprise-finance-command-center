const {test}=require('node:test');
const assert=require('node:assert/strict');
const M=require('../web/report-model.js'),P=require('../web/pnl-visual.js');
global.FinanceReport=M;
const record={month:'2026-08',entity:'US01',division:'Hardware',revenue:123456.78,marginal_contribution:100,gross_profit:90,opex:120,depreciation:10,ebit:-40,net_income:-50};
test('evidence exports raw EUR and missing comparisons without rounded display values',()=>{
 const data={meta:{end_month:'2026-08'},management_detail:[record]};
 const csv=P.csv(data,{entity:'all',division:'all'},'ebit',M);
 assert.match(csv,/"actual_eur","prior_eur"/);
 assert.match(csv,/"US01","Hardware",-40,"","","",1,"management_detail"/);
 assert.match(P.csv(data,{entity:'all',division:'all'},'revenue',M),/,123456\.78,/);
 assert.equal(P.csv(data,{entity:'ES01',division:'all'},'revenue',M).split('\r\n').length,1);
});
test('export escapes labels and neutralizes spreadsheet formula prefixes without changing negative numbers',()=>{
 const data={meta:{end_month:'2026-08'},management_detail:[{...record,entity:'=1+1',division:'Hardware, "test"'}]};
 const csv=P.csv(data,{entity:'all',division:'all'},'ebit',M);
 assert.match(csv,/"'=1\+1"/);assert.match(csv,/"Hardware, ""test"""/);assert.match(csv,/,-40,/);
});

test('missing P&L data produces no fabricated bars or percentage markers',()=>{
 const html=P.render({}, {}, '2026-08','All entities');
 assert.doesNotMatch(html,/<i style=/);
 assert.doesNotMatch(html,/NaN|undefined/);
});
test('negative percentage changes use the left endpoint independently of favorable cost polarity',()=>{
 const html=P.render({...record,opex:100},{...record,opex:120},'2026-08','All entities');
 assert.match(html,/pnl-percent good negative/);
 assert.match(html,/-16.7%/);
});
test('inline P&L inspector preserves negative signs and names its management-summary source',()=>{
 const data={meta:{end_month:'2026-08'},management_detail:[{...record,ebit:-1250000}]};
 const html=P.inspector(data,{entity:'all',division:'all'},'ebit');
 assert.match(html,/-€1\.3m/);
 assert.match(html,/management_detail · management summary/);
 assert.match(html,/not individual ledger postings/);
 assert.doesNotMatch(html,/NaN|undefined|Source-to-scope difference/);
});

test('source detail hides only zero-to-zero activity and preserves it in the full CSV export',()=>{
 const data={meta:{end_month:'2026-08'},management_detail:[
  {...record,month:'2026-08',entity:'US01'},
  {...record,month:'2025-08',entity:'US01',revenue:100000},
  {...record,month:'2026-08',entity:'CN01',revenue:0,marginal_contribution:0,gross_profit:0,opex:0,depreciation:0,ebit:0,net_income:0},
  {...record,month:'2025-08',entity:'CN01',revenue:0,marginal_contribution:0,gross_profit:0,opex:0,depreciation:0,ebit:0,net_income:0},
 ]};
 const detail=P.detail(data,{entity:'all',division:'all'},'revenue');
 assert.match(detail,/US01 \/ Hardware/);
 assert.doesNotMatch(detail,/CN01 \/ Hardware/);
 assert.match(detail,/1 zero-activity combination omitted from this view and retained in CSV export/);
 const csv=P.csv(data,{entity:'all',division:'all'},'revenue',M);
 assert.match(csv,/"CN01","Hardware",0,0,0,/);
});
test('source detail explains when a selection has only zero activity',()=>{
 const zero={...record,entity:'CN01',revenue:0,marginal_contribution:0,gross_profit:0,opex:0,depreciation:0,ebit:0,net_income:0};
 const data={meta:{end_month:'2026-08'},management_detail:[zero,{...zero,month:'2025-08'}]};
 const detail=P.detail(data,{entity:'all',division:'all'},'revenue');
 assert.match(detail,/No current or prior-year activity for this line in the selected scope/);
 assert.match(detail,/1 zero-activity combination omitted/);
});
