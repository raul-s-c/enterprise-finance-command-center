const {test}=require('node:test');
const assert=require('node:assert/strict');
global.FinanceReport=require('../web/report-model.js');
require('../web/report-charts.js');
global.ReportContext=require('../web/report-context.js');
require('../web/management-book.js');
const data=require('../web/data/dashboard.json');
const render=scope=>global.ManagementBook.executivePages(data,scope,'')[0].html;
const detail=(html,key)=>html.match(new RegExp(`<template data-story-detail="${key}">([\\s\\S]*?)</template>`))[1];

test('filtered Executive keeps consolidated evidence distinct from operating evidence',()=>{
  const html=render({entity:'US01',division:'Hardware'});
  assert.match(detail(html,'revenue'),/US01 · Hardware/);
  for(const key of ['free-cash-flow','net-working-capital']){
    assert.match(detail(html,key),/Consolidated group · all entities and divisions/);
    assert.doesNotMatch(detail(html,key),/US01 · Hardware/);
  }
  assert.match(html,/Consolidated group · not filtered/);
  assert.match(html,/Published scopes · owner, due date and lifecycle/);
  assert.match(detail(html,'gross-margin'),/pp vs PY/);
  assert.doesNotMatch(html,/data-story-view=""/);
  const rows=[...html.matchAll(/data-story-division="([^"]+)"[\s\S]*?<strong>([^<]+)<\/strong>/g)];
  assert.equal(rows.length,1);
  assert.equal(rows[0][1],'Hardware');
  const expected=global.FinanceReport.aggregate(data.management_detail,{entity:'US01',division:'Hardware'}).find(row=>row.month===data.meta.end_month).ebit;
  assert.equal(rows[0][2],global.ReportCharts.money(expected));
});

test('Executive narrative ties the result to scoped commercial drivers, source keys and a clearly labelled group outlook',()=>{
  const group=render({entity:'all',division:'all'});
  assert.match(group,/aria-label="Executive narrative"/);
  assert.match(group,/RESULT · 2026-08 close/);
  assert.match(group,/Revenue [^<]+ vs PY · EBIT [^<]+ vs PY/);
  assert.match(group,/WHY IT MOVED · All entities · All divisions/);
  assert.match(group,/Price [^<]+ · Volume [^<]+ · Mix [^<]+/);
  assert.match(group,/Review source · price_volume_mix.csv · 2026-08|All|price_effect/);
  assert.match(group,/OUTLOOK &amp; RESPONSE · GROUP OUTLOOK/);
  assert.match(group,/FY EBIT outlook is .*below budget/);
  assert.match(group,/data-story-view="action-execution"/);

  const filtered=render({entity:'US01',division:'Hardware'});
  assert.match(filtered,/Selected scope · US01 · Hardware/);
  assert.match(filtered,/WHY IT MOVED · US01 · Hardware/);
  assert.match(filtered,/OUTLOOK &amp; RESPONSE · GROUP OUTLOOK/);
  assert.doesNotMatch(filtered,/Group mix reduced year-on-year revenue/);

  const unsupported=render({entity:'CZ01',division:'Events'});
  assert.match(unsupported,/No comparable published driver is available for this exact scope/);
  assert.match(unsupported,/No active action is assigned to this exact scope/);
  assert.match(unsupported,/GROUP OUTLOOK/);
});
