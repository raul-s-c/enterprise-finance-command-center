const {test,expect}=require('@playwright/test');

test('Balance Sheet shows asset history beside its reconciled equation on a laptop',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=balance-sheet&page=0');
  const cockpit=page.locator('.balance-cockpit');
  await expect(cockpit.locator('.sw-positive-month')).toHaveCount(12);
  await expect(cockpit.locator('.sw-secondary .sw-formula')).toBeVisible();
  await expect(cockpit.locator('.sw-structure span')).toHaveCount(4);
  const close=await page.evaluate(async()=>{
    const data=await(await fetch('/data/dashboard.json')).json();
    return data.balance_sheet.at(-1);
  });
  expect(close.assets-close.liabilities-close.equity).toBeCloseTo(0,2);
  const fit=await cockpit.locator('.sw-grid').evaluate(grid=>({
    overflow:grid.scrollHeight-grid.clientHeight,
    trend:grid.querySelector('.sw-primary').getBoundingClientRect(),
    equation:grid.querySelector('.sw-secondary').getBoundingClientRect()
  }));
  expect(fit.overflow).toBeLessThanOrEqual(1);
  expect(fit.trend.right).toBeLessThanOrEqual(fit.equation.left+1);
  for(const selector of ['.sw-primary','.sw-secondary']){
    expect(await cockpit.locator(selector).evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(5);
});

test('Balance Sheet keeps funding components alongside trend and equation on a tall desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=balance-sheet&page=0');
  const cockpit=page.locator('.balance-cockpit');
  await expect(cockpit).toContainText('Consolidated group');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(5);
});

test('Balance Sheet retains KPI evidence above the 1500px breakpoint',async({page})=>{
  await page.setViewportSize({width:1501,height:720});
  await page.goto('/#view=balance-sheet&page=0');
  const cockpit=page.locator('.balance-cockpit');
  await expect(cockpit.locator('.sw-primary')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toBeVisible();
  await expect(cockpit.locator('.sw-inspector')).toBeHidden();
  await cockpit.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  expect(await cockpit.locator('.sw-detail').evaluate(element=>element.scrollHeight-element.clientHeight)).toBeLessThanOrEqual(1);
});
