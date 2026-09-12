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
  assert.match(detail(html,'gross-margin'),/pp vs PY/);
  assert.doesNotMatch(html,/data-story-view=""/);
  const rows=[...html.matchAll(/data-story-division="([^"]+)"[\s\S]*?<strong>([^<]+)<\/strong>/g)];
  assert.equal(rows.length,1);
  assert.equal(rows[0][1],'Hardware');
  const expected=global.FinanceReport.aggregate(data.management_detail,{entity:'US01',division:'Hardware'}).find(row=>row.month===data.meta.end_month).ebit;
  assert.equal(rows[0][2],global.ReportCharts.money(expected));
});
