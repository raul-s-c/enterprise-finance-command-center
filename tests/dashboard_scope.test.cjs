const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
function context(){
  const ctx = vm.createContext({Intl, Map, Set, Number, String, Array});
  vm.runInContext(fs.readFileSync(path.join(root, 'web/app.js'), 'utf8'), ctx);
  return ctx;
}
test('mobile charts retain every value and expose at most five evenly spaced ticks',()=>{
  const ctx=context();
  for(const count of [1,2,5,12,24,36]){
    const html=vm.runInContext(`bars(Array.from({length:${count}},(_,i)=>({month:'2026-'+String(i+1).padStart(2,'0'),value:i+1})), 'value')`,ctx);
    assert.equal((html.match(/class="bar-wrap/g)||[]).length,count);
    assert.equal((html.match(/mobile-tick/g)||[]).length,Math.min(5,count));
    assert.equal((html.match(/aria-label=/g)||[]).length,count);
    assert.match(html,/class="bar-wrap mobile-tick"/);
  }
});
test('Executive clearly distinguishes filtered operating values from group measures',()=>{
  const ctx=context();
  vm.runInContext(`data={meta:{end_month:'2026-08'},management_detail:[{month:'2026-08',entity:'US01',division:'Software',revenue:100,ebit:20,gross_profit:70}],working_capital:[{net_working_capital:500}],cash_flow:[{free_cash_flow:200}]};state.entity='US01';state.division='Software';`,ctx);
  const html=vm.runInContext('renderExecutive()',ctx);
  assert.match(html,/Group free cash flow/);
  assert.match(html,/Group net working capital/);
  assert.match(html,/Consolidated · not filtered/);
  assert.match(html,/Group management commentary/);
  vm.runInContext(fs.readFileSync(path.join(root,'web/v21.js'),'utf8'),ctx);
  assert.match(vm.runInContext('renderers.executive()',ctx),/remain consolidated group measures/);
});
