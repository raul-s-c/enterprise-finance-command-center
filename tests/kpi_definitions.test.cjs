const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const definitions=require('../web/kpi-definitions.js');
const model=require('../web/report-model.js');

test('all rendered KPI cards have reviewed calculation, scope, period and source metadata',()=>{
  const ctx=vm.createContext({Intl,Map,Set,Number,String,Array});
  const html=fs.readFileSync(path.join(root,'web/index.html'),'utf8');
  for(const match of html.matchAll(/<script src="([^"?]+)/g)){
    if(match[1].startsWith('report-')||match[1]==='kpi-definitions.js')continue;
    vm.runInContext(fs.readFileSync(path.join(root,'web',match[1]),'utf8'),ctx);
  }
  ctx.fixture=JSON.parse(fs.readFileSync(path.join(root,'web/data/dashboard.json'),'utf8'));
  const labels=vm.runInContext(`
    data=fixture;const captured=new Set();
    kpi=(label)=>{captured.add(label);return '';};
    for(const entity of ['all',...new Set(data.management_detail.map(r=>r.entity))]){
      for(const division of ['all',...new Set(data.management_detail.map(r=>r.division))]){
        state.entity=entity;state.division=division;
        for(const render of Object.values(renderers))render();
      }
    }
    [...captured];`,ctx);
  assert.ok(labels.length>90,`Expected broad coverage, got ${labels.length}`);
  for(const label of labels){
    const definition=definitions.get(label);
    assert.ok(definition,`Missing KPI definition: ${label}`);
    for(const key of ['formula','source','scope','period'])assert.ok(definition[key]?.trim().length>0,`${label}: missing ${key}`);
  }
});

test('stock, flow and consolidated scope are distinguished',()=>{
  assert.match(definitions.get('12M forecast assets').formula,/not a sum/);
  assert.match(definitions.get('12M forecast revenue').formula,/Sum/);
  assert.match(definitions.get('Group free cash flow').scope,/filters do not apply/);
  assert.match(definitions.get('Current actual impact').scope,/filters do not apply/);
  assert.match(definitions.get('Translation reserve').scope,/all divisions/);
  assert.match(definitions.get('NRR').formula,/New customers are excluded/);
  assert.match(definitions.get('Net leverage').formula,/trailing-12-month EBITDA/);
  assert.equal(definitions.get('Unreviewed KPI'),null);
});

test('untrusted route indices cannot address a fractional or infinite subpage',()=>{
  for(const value of ['1.5',1.5])assert.equal(model.pageIndex(value),1);
  for(const value of ['Infinity','NaN','junk',-1,null,undefined])assert.equal(model.pageIndex(value),0);
  assert.equal(model.pageIndex('12'),12);
});

test('Events KPI aggregation is not truncated to the table display limit',()=>{
  const ctx=vm.createContext({Intl,Map,Set,Number,String,Array});
  for(const file of ['app.js','v05.js'])vm.runInContext(fs.readFileSync(path.join(root,'web',file),'utf8'),ctx);
  const result=vm.runInContext(`
    const values={};kpi=(label,value)=>{values[label]=value;return '';};
    data={events_summary:[{month:'2026-08',bookings:999}],events_backlog_detail:Array.from({length:35},()=>({entity:'US01',bookings:10,recognized_revenue:5,ending_backlog:20}))};
    state.entity='US01';eventsBlock();values['Bookings'];`,ctx);
  assert.equal(result,vm.runInContext('eur.format(350)',ctx));
  const empty=vm.runInContext(`state.entity='CZ01';eventsBlock();values['Bookings'];`,ctx);
  assert.equal(empty,vm.runInContext('eur.format(0)',ctx));
});

test('an empty workforce filter never substitutes the consolidated headcount',()=>{
  const ctx=vm.createContext({Intl,Map,Set,Number,String,Array});
  for(const file of ['app.js','v05.js','v14.js'])vm.runInContext(fs.readFileSync(path.join(root,'web',file),'utf8'),ctx);
  const result=vm.runInContext(`
    const values={};kpi=(label,value)=>{values[label]=value;return '';};
    data={workforce_summary:[{month:'2026-08',ending_fte:999}],workforce_detail:[{entity:'US01',division:'Software',ending_fte:5}]};
    state.entity='CZ01';state.division='Events';workforceBlock();values['Ending FTE'];`,ctx);
  assert.equal(result,vm.runInContext('num(0,1)',ctx));
});
