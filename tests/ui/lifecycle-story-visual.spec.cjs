const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');
const groupActions=published.management_actions.filter(row=>row.scope_level==='Group');
const groupHistory=published.management_action_history.filter(row=>row.scope_level==='Group');
const groupOverdue=groupActions.filter(row=>['Open','In Progress'].includes(row.status)&&row.overdue===true);
const duePreviewCount=Math.min(3,groupOverdue.length||groupActions.filter(row=>['Open','In Progress'].includes(row.status)).length);

test('Performance Review tells the controlled lifecycle story without fake history',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=performance-review&page=2');
  await expect(page.locator('.plv-status')).toBeVisible();
  const composition=['Open','In Progress','Closed','Cancelled'].map(status=>({status,count:groupActions.filter(row=>row.status===status).length})).filter(item=>item.count).map(item=>`${item.count} ${item.status}`).join(', ');
  await expect(page.locator('.plv-composition')).toHaveAttribute('aria-label',`Status composition: ${composition}`);
  if(new Set(groupHistory.map(row=>row.snapshot_month)).size===1)await expect(page.locator('.plv-first-snapshot')).toContainText('First controlled snapshot');
  else await expect(page.locator('.plv-history-bars')).toBeVisible();
  if(groupOverdue.length)await expect(page.locator('.plv-overdue-warning')).toContainText(`${groupOverdue.length} overdue`);
  else await expect(page.locator('.plv-overdue-clear')).toContainText(`No overdue actions at the ${published.meta.end_month} close`);
  await expect(page.locator('.plv-due-row')).toHaveCount(duePreviewCount);
  await expect(page.locator('#entityFilter').locator('..')).toBeVisible();
  for(const summary of await page.locator('.plv-records>summary').all())await expect(summary).toBeInViewport();
  await page.screenshot({path:'test-results/lifecycle-story-desktop.png',fullPage:true});
  await page.locator('[data-plv-register]').click();
  await expect(page.locator('#reportPageSelect')).toHaveValue('3');
});

test('lifecycle page remains separate and reachable on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=performance-review&page=2');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  if(new Set(groupHistory.map(row=>row.snapshot_month)).size===1)await expect(page.locator('.plv-first-snapshot')).toBeVisible();
  else await expect(page.locator('.plv-history-bars')).toBeVisible();
  await page.screenshot({path:'test-results/lifecycle-story-mobile.png',fullPage:true});
  const regions=page.getByRole('navigation',{name:'Dashboard regions'});
  await regions.getByRole('button').nth(1).click();
  await expect(page.locator(groupOverdue.length?'.plv-overdue-warning':'.plv-overdue-clear')).toBeVisible();
  await expect(page.locator('.plv-due-row')).toHaveCount(duePreviewCount);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/lifecycle-overdue-mobile.png',fullPage:true});
});

test('lifecycle and due-date panels share an honest entity scope',async({page})=>{
  await page.goto('/#view=performance-review&page=2&entity=US01&division=all');
  await expect(page.locator('#reportContext')).toContainText('Entity: US01');
  const entityActions=published.management_actions.filter(row=>row.scope_level==='Entity'&&row.entity==='US01');
  await expect(page.locator('.plv-status .plv-heading').first()).toContainText(`${entityActions.length} management actions`);
  const entityComposition=['Open','In Progress','Closed','Cancelled'].map(status=>({status,count:entityActions.filter(row=>row.status===status).length})).filter(item=>item.count).map(item=>`${item.count} ${item.status}`).join(', ');
  await expect(page.locator('.plv-composition')).toHaveAttribute('aria-label',`Status composition: ${entityComposition}`);
  await expect(page.locator('.plv-due')).toBeVisible();
});
