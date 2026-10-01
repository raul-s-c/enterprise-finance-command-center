const {test,expect}=require('@playwright/test');

test('review evidence leads with variance and accountable action state',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=performance-review&page=1');
  const panels=page.locator('.story-composite>.panel');
  await expect(panels).toHaveCount(2);
  await expect(panels.first().locator('thead th:visible')).toHaveText(['Metric','Actual','Benchmark','Variance']);
  await expect(panels.last().locator('thead th:visible')).toHaveText(['Trigger / priority','Owner','Due','Status']);
  const drivers=await panels.first().locator('tbody tr').evaluateAll(rows=>rows.map(row=>({metric:row.cells[0]?.textContent?.trim(),variance:row.querySelector('.review-variance')?.className||'',title:row.querySelector('.review-variance')?.title||''})));
  expect(drivers.find(row=>row.metric==='OPEX')).toMatchObject({variance:expect.stringContaining('is-adverse'),title:'Adverse financial variance'});
  expect(drivers.find(row=>row.metric==='Revenue')).toMatchObject({variance:expect.stringContaining('is-favorable'),title:'Favorable financial variance'});
  await expect(panels.last().locator('tbody tr').first()).toContainText('Open');
  for(const panel of await panels.all())expect(await panel.evaluate(el=>el.scrollHeight<=el.clientHeight+1)).toBe(true);
  await page.screenshot({path:'test-results/review-evidence-columns.png',fullPage:true});
});

test('review tabs fit a short laptop while retaining full accessible titles',async({page})=>{
  await page.setViewportSize({width:1024,height:720});
  await page.goto('/#view=performance-review&page=0');
  const tabs=page.locator('#reportTabs button');
  await expect(tabs).toHaveText(['Review story','Drivers & actions','Lifecycle','Action register']);
  for(const tab of await tabs.all()){
    expect(await tab.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
    expect((await tab.getAttribute('aria-label')).length).toBeGreaterThan((await tab.textContent()).length);
  }
  await tabs.nth(1).click();
  await expect(page.locator('#reportPageNumber')).toContainText('2 / 4');
  await expect(page.locator('#reportPageSelect')).toHaveValue('1');
});
