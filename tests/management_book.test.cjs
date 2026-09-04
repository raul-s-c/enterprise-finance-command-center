const {test}=require('node:test');
const assert=require('node:assert/strict');
global.ReportContext={group:{key:'group'}};
global.FinanceReport={escape:value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;')};
require('../web/management-book.js');
const B=global.ManagementBook;

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
