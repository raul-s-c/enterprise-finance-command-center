const {test,expect}=require('@playwright/test');

test('Executive Drivers, Outlook and Actions fit their laptop panels',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  for(const index of [1,2,3]){
    await page.goto(`/#view=executive&page=${index}`);
    await expect(page.locator('.story-board')).toBeVisible();
    const geometry=await page.locator('.story-board > *').evaluateAll(nodes=>nodes.map(node=>({name:node.className,client:node.clientHeight,scroll:node.scrollHeight})));
    expect(geometry.every(item=>item.scroll<=item.client+1),`Executive ${index}: ${JSON.stringify(geometry)}`).toBe(true);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    const screenshot=testInfo.outputPath(`executive-${index}-1280x720.png`);
    await page.screenshot({path:screenshot});
    await testInfo.attach(`executive-${index}-1280x720`,{path:screenshot,contentType:'image/png'});
  }
  await page.goto('/#view=executive&page=1');
  await expect(page.locator('.executive-mini-month')).toHaveCount(12);
  await page.locator('.executive-mini-trend [data-metric="ebit"]').click();
  await expect(page.locator('.executive-mini-trend h3')).toHaveText('EBIT performance');
  await expect(page.locator('.executive-mini-month')).toHaveCount(12);
  await page.locator('.executive-mini-month').first().click();
  await expect(page.locator('#reportDialog .month-detail')).toBeVisible();
  await page.goto('/#view=executive&page=2');
  await expect(page.locator('.executive-forecast-month')).toHaveCount(12);
  await expect(page.locator('.story-scenario')).toHaveCount(3);
});

test('Executive keeps its responsive chart reachable on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=executive&page=1');
  await expect(page.locator('.report-trend .chart-point')).toHaveCount(6);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('Close Journey evidence links and CTA fit at laptop height',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=close-journey');
  const evidence=page.locator('.cj-evidence');
  await expect(evidence).toBeVisible();
  const size=await evidence.evaluate(element=>({client:element.clientHeight,scroll:element.scrollHeight}));
  expect(size.scroll,JSON.stringify(size)).toBeLessThanOrEqual(size.client+1);
  await expect(page.locator('#cj-open-evidence')).toBeInViewport();
});
