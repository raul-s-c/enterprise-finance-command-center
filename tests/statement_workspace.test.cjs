const {test}=require('node:test');
const assert=require('node:assert/strict');
global.FinanceReport=require('../web/report-model.js');
require('../web/report-charts.js');
global.ReportContext=require('../web/report-context.js');
require('../web/statement-workspace.js');
const data=require('../web/data/dashboard.json');

test('core financial statements open with a premium one-screen cockpit',()=>{
  const state={entity:'all',division:'all'};
  for(const view of ['pnl','cash-flow','balance-sheet']){
    const pages=global.StatementWorkspace.pages(view,data,state);
    assert.equal(pages.length,1,view);
    assert.equal(pages[0].custom,true,view);
    assert.equal(pages[0].fullScreen,true,view);
    assert.match(pages[0].html,/statement-workspace/,view);
    assert.match(pages[0].html,/Evidence inspector/,view);
    assert.equal((pages[0].html.match(/class="sw-kpi"/g)||[]).length,5,view);
    assert.doesNotMatch(pages[0].html,/undefined|NaN/,view);
  }
});

test('statement cockpits preserve reconciliation language and evidence routes',()=>{
  const state={entity:'all',division:'all'};
  const pnl=global.StatementWorkspace.pages('pnl',data,state)[0].html;
  const cash=global.StatementWorkspace.pages('cash-flow',data,state)[0].html;
  const balance=global.StatementWorkspace.pages('balance-sheet',data,state)[0].html;
  assert.match(pnl,/no balancing plug/i);
  assert.match(cash,/Operating cash flow \+ investing cash flow/);
  assert.match(balance,/Assets − liabilities − equity/);
  for(const html of [pnl,cash,balance])assert.match(html,/Reconciled to the published close/);
});
