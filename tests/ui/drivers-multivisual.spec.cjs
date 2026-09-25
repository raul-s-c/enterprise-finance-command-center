const {test,expect}=require('@playwright/test');

test('Business Drivers connects five operating values to the financial chain on a laptop',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=business-drivers&page=0');
  const cockpit=page.locator('.drivers-cockpit');
  await expect(cockpit.locator('.sw-primary .sw-ranking button')).toHaveCount(5);
  await expect(cockpit.locator('.sw-secondary .sw-driver-chain')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toContainText('P&L · cash · balance');
  for(const selector of ['.sw-primary','.sw-secondary']){
    expect(await cockpit.locator(selector).evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await cockpit.locator('.sw-primary .sw-ranking button').first().click();
  await expect(page.locator('#reportDialog')).toContainText('software_summary');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(5);
});

test('Business Drivers shows operating health beneath values and chain on tall desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=business-drivers&page=0');
  const cockpit=page.locator('.drivers-cockpit');
  await expect(cockpit).toContainText('Consolidated group');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await expect(cockpit.locator('.sw-detail')).toContainText('Driver health');
});

test('Business Drivers keeps KPI evidence reachable at short desktop heights',async({page})=>{
  await page.setViewportSize({width:1501,height:720});
  await page.goto('/#view=business-drivers&page=0');
  const cockpit=page.locator('.drivers-cockpit');
  await expect(cockpit.locator('.sw-primary')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toBeVisible();
  await expect(cockpit.locator('.sw-inspector')).toBeHidden();
  await cockpit.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
});

test('Business Drivers never compares unlike units with shared bars on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=business-drivers&page=0');
  const cockpit=page.locator('.drivers-cockpit');
  await expect(cockpit.locator('.sw-primary .sw-ranking button')).toHaveCount(5);
  await expect(cockpit.locator('.sw-primary')).toContainText('ARR (annualised)');
  await expect(cockpit.locator('.sw-primary')).toContainText('revenue (month)');
  const bars=await cockpit.locator('.sw-primary .sw-ranking i,.sw-detail .sw-ranking i').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).display));
  expect(bars).toHaveLength(10);
  expect(bars.every(display=>display==='none')).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
});
