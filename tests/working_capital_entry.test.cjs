const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

test('working capital leads with contribution while preserving all evidence sections',()=>{
  const source=fs.readFileSync('web/report-workspace.js','utf8');
  const fn=source.slice(source.indexOf('function reportPages(){'),source.indexOf('function reportReadRoute(){'));
  const context={state:{view:'working-capital'},data:{},reportLegacyPages:()=>[{title:'Aging evidence'}],reportCurrent:()=>({}),ContributionExplorer:{pages:()=>[{title:'Net working capital contribution'},{title:'Receivables contribution'}]},ManagementBook:{compose:pages=>pages}};
  vm.createContext(context);
  vm.runInContext(fn,context);
  assert.deepEqual(Array.from(context.reportPages(),p=>p.title),['Net working capital contribution','Receivables contribution','Aging evidence']);
  context.state.view='cash-flow';
  assert.equal(context.reportPages()[0].title,'Aging evidence');
});
