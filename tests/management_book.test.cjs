const {test}=require('node:test');
const assert=require('node:assert/strict');
global.ReportContext={group:{key:'group'}};
global.FinanceReport={escape:value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;')};
require('../web/management-book.js');
const B=global.ManagementBook;

test('definitions stay next to evidence instead of creating a sparse standalone page',()=>{
  const result=B.compose([{title:'Evidence',html:'<table></table>'},{title:'Context & definitions',html:'<p>Calculation basis</p>'}]);
  assert.equal(result.length,1);
  assert.match(result[0].html,/<details class="report-definitions">/);
  assert.match(result[0].html,/Calculation basis/);
});

test('KPI bands are attached to evidence, never paired as a KPI-only destination',()=>{
  const result=B.compose([
    {title:'Operating indicators',html:'<div class="report-indicators">Revenue</div>',policy:{key:'group'}},
    {title:'Cash indicators',html:'<div class="report-indicators">Cash</div>',policy:{key:'group'}},
    {title:'Trend',html:'<svg aria-label="Revenue trend"></svg>',policy:{key:'group'}},
    {title:'Bridge',html:'<svg aria-label="Cash bridge"></svg>',policy:{key:'group'}}
  ]);
  assert.ok(result.every(page=>!page.html.includes('report-indicators')||page.html.includes('<svg')));
  assert.equal(result.filter(page=>page.html.includes('Revenue</div>')).length,1);
  assert.equal(result.filter(page=>page.html.includes('Cash</div>')).length,1);
});

test('cash detail keeps published-close KPIs but leaves forecast horizons in Plan & Outlook',()=>{
  const previous=global.state;
  global.state={view:'cash-flow'};
  try{
    const result=B.compose([
      {title:'Cash indicators',html:'<div class="report-indicators"><div class="kpi"><div class="kpi-label">Operating cash flow</div><div class="kpi-note">Compare to the 12M forecast</div></div></div>',policy:{key:'group'}},
      {title:'Forecast indicators',html:'<div class="report-indicators"><div class="kpi"><div class="kpi-label">24M forecast OCF</div></div></div>',policy:{key:'group'}},
      {title:'Latest cash bridge',html:'<article>cash bridge</article>',policy:{key:'group'}},
      {title:'Cash trend',html:'<article>cash trend</article>',policy:{key:'group'}}
    ]);
    assert.match(result[0].html,/cash-detail-board/);
    assert.match(result[0].html,/Operating cash flow/);
    assert.doesNotMatch(result[0].html,/24M forecast OCF/);
    assert.equal((result[0].html.match(/class="kpi"/g)||[]).length,1);
  }finally{
    if(previous===undefined)delete global.state;
    else global.state=previous;
  }
});

test('a full-screen cockpit cannot be swallowed by a preceding legacy page',()=>{
  const cockpit={title:'Cockpit',fullScreen:true,html:'<svg></svg>'};
  const result=B.compose([{title:'Context',html:'context'},cockpit]);
  assert.equal(result.length,2);
  assert.equal(result[1],cockpit);
});

test('management-book composition preserves every source section and pairs sparse pages',()=>{
  const pages=Array.from({length:7},(_,i)=>({title:`Section ${i+1}`,html:`<p>${i+1}</p>`,policy:{key:'group'}}));
  const result=B.compose(pages);
  assert.equal(result.length,4);
  for(const page of pages)assert.equal(result.filter(r=>r.html.includes(`data-source-section="${page.title}"`)).length,1);
  assert.match(result[0].title,/Section 1 · Section 2/);
});

test('mixed-scope compositions disclose group context instead of one misleading filter scope',()=>{
  const result=B.compose([{title:'A',html:'a',policy:{key:'operating'}},{title:'B',html:'b',policy:{key:'group'}}]);
  assert.equal(result[0].policy.key,'group');
});

test('contribution workspaces remain full-screen between composed report sections',()=>{
  const contribution={title:'Receivables contribution',html:'<section data-contribution="ar"></section>',policy:{key:'group'},custom:true,contribution:true};
  const result=B.compose([
    {title:'A',html:'a',policy:{key:'group'}},
    {title:'B',html:'b',policy:{key:'group'}},
    contribution,
    {title:'C',html:'c',policy:{key:'group'}},
    {title:'D',html:'d',policy:{key:'group'}}
  ]);
  assert.equal(result.length,3);
  assert.equal(result[1],contribution);
  assert.match(result[2].title,/C · D/);
});
