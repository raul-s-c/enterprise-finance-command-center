const {test,expect}=require('@playwright/test');

test('Executive Drivers, Outlook and Actions fit their laptop panels',async({page},testInfo)=>{
  for(const viewport of [{width:1024,height:768},{width:1280,height:720},{width:1366,height:768}]){
    await page.setViewportSize(viewport);
    for(const index of [1,2,3]){
      await page.goto(`/#view=executive&page=${index}`);
      await expect(page.locator('.story-board')).toBeVisible();
      const geometry=await page.locator('.story-board > *').evaluateAll(nodes=>nodes.map(node=>({name:node.className,client:node.clientHeight,scroll:node.scrollHeight})));
      expect(geometry.every(item=>item.scroll<=item.client+1),`Executive ${index} at ${viewport.width}x${viewport.height}: ${JSON.stringify(geometry)}`).toBe(true);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      if(viewport.width<=1280){
        const screenshot=testInfo.outputPath(`executive-${index}-${viewport.width}x${viewport.height}.png`);
        await page.screenshot({path:screenshot});
        await testInfo.attach(`executive-${index}-${viewport.width}x${viewport.height}`,{path:screenshot,contentType:'image/png'});
      }
    }
  }
  await page.setViewportSize({width:1280,height:720});
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

test('Executive overview gives compact laptops a full-width, reachable region selector',async({page})=>{
  await page.setViewportSize({width:1024,height:720});
  await page.goto('/#view=executive&page=0');
  const switcher=page.getByRole('navigation',{name:'Executive overview regions'});
  await expect(switcher).toBeVisible();
  const labels=['Performance trend','EBIT contribution','Cash drivers','Company story'];
  const analytics=page.locator('.tower-analytics');
  for(let index=0;index<labels.length;index++){
    await switcher.getByRole('button',{name:labels[index],exact:true}).click();
    const region=page.locator(`#executive-region-${index}`);
    await expect(region).toBeVisible();
    const layout=await region.evaluate(element=>({width:element.getBoundingClientRect().width,parent:element.parentElement.getBoundingClientRect().width}));
    expect(layout.width,JSON.stringify({label:labels[index],...layout})).toBeGreaterThanOrEqual(layout.parent-2);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  await expect(page.locator('.tower-actions')).toBeVisible();
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
