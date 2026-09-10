const {test}=require('node:test');
const assert=require('node:assert/strict');
global.FinanceReport=require('../web/report-model.js');
require('../web/report-charts.js');
global.ReportContext=require('../web/report-context.js');
require('../web/statement-workspace.js');
const data=require('../web/data/dashboard.json');

test('core finance and operating modules open with a premium one-screen cockpit',()=>{
  const state={entity:'all',division:'all'};
  for(const view of ['pnl','cash-flow','balance-sheet','forecast','macro-sensitivities','treasury','business-drivers','profitability','intercompany','operations-capex','fx']){
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

test('driver, consolidation and FX cockpits keep accounting paths explicit',()=>{
  const state={entity:'all',division:'all'};
  const macro=global.StatementWorkspace.pages('macro-sensitivities',data,state)[0].html;
  const drivers=global.StatementWorkspace.pages('business-drivers',data,state)[0].html;
  const intercompany=global.StatementWorkspace.pages('intercompany',data,state)[0].html;
  const fx=global.StatementWorkspace.pages('fx',data,state)[0].html;
  assert.match(macro,/scenarios must never be added/);
  assert.match(macro,/Gross profit impact/);
  assert.match(macro,/selection applies to sensitivities only/);
  assert.match(macro,/data-sw-detail="ma-shock-energy-index-10"/);
  assert.match(drivers,/Operational evidence precedes accounting output/);
  assert.match(drivers,/Opening FTE \+ hires − attrition/);
  assert.match(drivers,/-36\.2% vs 2026-07/);
  assert.doesNotMatch(drivers,/— vs 2026-07/);
  assert.match(intercompany,/Revenue &amp; COGS eliminated/);
  assert.match(intercompany,/Maximum reciprocal, revenue and EBIT consolidation gap/);
  assert.match(fx,/Transaction remeasurement never enters CTA/);
  assert.match(fx,/Open foreign-currency receivables − payables/);
  assert.match(fx,/All entities · all divisions/);
  assert.match(fx,/data-sw-detail="fx-currency-czk"/);
  for(const html of [macro,drivers,intercompany,fx]){
    assert.match(html,/Reconciled to the published close/);
    assert.doesNotMatch(html,/undefined|NaN/);
  }
});

test('operating cockpits expose linked calculations without inventing missing allocations',()=>{
  const state={entity:'all',division:'all'};
  const forecast=global.StatementWorkspace.pages('forecast',data,state)[0].html;
  const treasury=global.StatementWorkspace.pages('treasury',data,state)[0].html;
  const profitability=global.StatementWorkspace.pages('profitability',data,state)[0].html;
  const operations=global.StatementWorkspace.pages('operations-capex',data,state)[0].html;
  assert.match(forecast,/One forecast · three linked statements/);
  assert.match(forecast,/Balance check/);
  assert.match(treasury,/Cash − minimum operating cash \+ undrawn RCF/);
  assert.match(treasury,/Post-pooling position/);
  assert.match(profitability,/Revenue − variable production cost − variable selling cost/);
  assert.match(profitability,/entity_product_profitability \+ customer_profitability/);
  assert.match(operations,/GO_LIVE is excluded/);
  assert.match(operations,/PPE at go-live/);
  assert.match(operations,/vs 2026-07/);
  assert.doesNotMatch(operations,/— vs 2026-07/);
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
