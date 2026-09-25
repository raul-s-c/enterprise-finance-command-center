const {test,expect}=require('@playwright/test');

test('Planning shows the rolling revenue outlook beside linked statement consequences',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=0');
  const cockpit=page.locator('.forecast-cockpit');
  await expect(cockpit.locator('.sw-forecast-month')).toHaveCount(12);
  await expect(cockpit.locator('.sw-secondary .sw-formula')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toContainText('Base scenario');
  for(const selector of ['.sw-primary','.sw-secondary']){
    expect(await cockpit.locator(selector).evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await cockpit.locator('.sw-forecast-month').first().click();
  await expect(page.locator('#reportDialog')).toContainText('forecast_cash_flow');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(3);
});

test('Planning displays scenarios with outlook and linked statements on a tall desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=forecast&page=0');
  const cockpit=page.locator('.forecast-cockpit');
  await expect(cockpit).toContainText('Consolidated group');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  for(const scenario of ['Base','Upside','Downside'])await expect(cockpit.locator('.sw-detail')).toContainText(scenario);
});

test('Planning keeps KPI evidence available just above the desktop breakpoint',async({page})=>{
  await page.setViewportSize({width:1501,height:720});
  await page.goto('/#view=forecast&page=0');
  const cockpit=page.locator('.forecast-cockpit');
  await expect(cockpit.locator('.sw-primary')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toBeVisible();
  await expect(cockpit.locator('.sw-inspector')).toBeHidden();
  await cockpit.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(3);
});
