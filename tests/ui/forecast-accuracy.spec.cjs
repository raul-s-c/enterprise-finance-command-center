const {test,expect}=require('@playwright/test');

test('forecast accuracy shows its full horizon evidence on a laptop',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=4');
  await expect(page.getByText('Forecast accuracy',{exact:true})).toBeVisible();
  await expect(page.locator('.fv-error-point')).toHaveCount(18);
  await expect(page.locator('.fv-bias-chart rect')).toHaveCount(18);
  await expect(page.locator('.fv-scenario')).toHaveCount(3);
  await expect(page.locator('.fv-scenario').first()).toContainText('€78.8M');
  await expect(page.locator('.fv-scenario').nth(1)).toContainText('€72.0M');
  await expect(page.locator('.fv-scenario').last()).toContainText('€83.4M');
  const fit=await page.locator('#content').evaluate(node=>{const insight=node.querySelector('.forecast-accuracy-visual .fv-insight').getBoundingClientRect(),bias=node.querySelector('.fv-bias-chart').getBoundingClientRect(),records=node.querySelector('.forecast-source-records').getBoundingClientRect();return {horizontal:document.documentElement.scrollWidth>innerWidth,panes:[...node.querySelectorAll('.story-composite')].map(pane=>Math.max(0,pane.scrollHeight-pane.clientHeight)),biasClear:bias.bottom<=insight.top+1,recordsClear:insight.bottom<=records.top+1};});
  expect(fit.horizontal).toBe(false);
  expect(fit.panes.every(overflow=>overflow<25)).toBe(true);
  expect(fit.biasClear).toBe(true);
  expect(fit.recordsClear).toBe(true);
  await page.screenshot({path:'test-results/forecast-accuracy.png',fullPage:true});
  for(const details of await page.locator('.forecast-source-records').all()){
    await details.locator('summary').click();
    await expect(details.locator('table')).toBeVisible();
    await details.locator('summary').click();
  }
  await page.setViewportSize({width:1024,height:768});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  const mobileFit=await page.locator('#content').evaluate(node=>{const panes=[...node.querySelectorAll('.story-composite')];return {overlap:panes[0].getBoundingClientRect().bottom>panes[1].getBoundingClientRect().top+1,firstOverflow:panes[0].scrollHeight-panes[0].clientHeight,secondOverflow:panes[1].scrollHeight-panes[1].clientHeight}});
  expect(mobileFit.overlap).toBe(false);
  expect(mobileFit.firstOverflow).toBeLessThan(2);
  expect(mobileFit.secondOverflow).toBeLessThan(2);
  await page.screenshot({path:'test-results/forecast-accuracy-mobile-first.png',fullPage:true});
  await page.locator('.story-composite').last().scrollIntoViewIfNeeded();
  await expect(page.getByText('Liquidity by forecast scenario',{exact:true})).toBeInViewport();
  await page.screenshot({path:'test-results/forecast-accuracy-mobile.png',fullPage:true});
});
