const {test}=require('node:test');
const assert=require('node:assert/strict');
const published=require('../web/data/dashboard.json');
require('../web/portfolio-decision-story.js');
const visual=globalThis.FinancePortfolioStory;

test('timeline spans exactly twelve calendar months and retains zero-event months',()=>{
  const months=visual.months(published.meta.end_month);
  assert.equal(months.length,12);
  assert.equal(months.at(-1),published.meta.end_month);
  const html=visual.story(published.portfolio_events,published.meta.end_month);
  const activeMonths=new Set(published.portfolio_events.filter(row=>months.includes(row.month)).map(row=>row.month));
  assert.equal((html.match(/data-pd-month=/g)||[]).length,activeMonths.size);
  assert.equal((html.match(/class="pd-inactive"/g)||[]).length,12-activeMonths.size);
  assert.doesNotMatch(html,/NaN|undefined/);
});

test('selected decision month displays only its source events and reasons',()=>{
  const month=published.meta.end_month;
  const rows=published.portfolio_events.filter(row=>row.month===month);
  const html=visual.story(published.portfolio_events,month,month);
  assert.equal((html.match(/class="pd-card /g)||[]).length,rows.length);
  for(const row of rows)assert.ok(html.includes(row.product));
  assert.match(html,/not assigned financial benefits/);
});

test('portfolio labels are escaped',()=>{
  const html=visual.story([{month:'2026-08',division:'<unsafe>',product_family:'& family',product:'P1',event:'PRODUCT_LAUNCH',effective_month:'2026-08',reason:'<bad>'}],'2026-08');
  assert.match(html,/&lt;unsafe&gt;/);
  assert.match(html,/&amp; family/);
  assert.doesNotMatch(html,/<unsafe>|<bad>/);
});
