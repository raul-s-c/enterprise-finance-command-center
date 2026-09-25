const {test,expect}=require('@playwright/test');

test('Cash Flow shows signed trend and reconciled cash identity together on a laptop',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=cash-flow&page=0');
  const cockpit=page.locator('.cash-cockpit');
  await expect(cockpit.locator('.sw-cash-month')).toHaveCount(12);
  await expect(cockpit.locator('.sw-secondary .sw-formula')).toBeVisible();
  const close=await page.evaluate(async()=>{
    const data=await(await fetch('/data/dashboard.json')).json();
    return data.cash_flow.at(-1);
  });
  expect(close.operating_cash_flow+close.investing_cash_flow-close.free_cash_flow).toBeCloseTo(0,2);
  await expect(cockpit.locator('.sw-secondary')).toContainText('€'+(close.free_cash_flow/1e6).toFixed(1)+'m');
  const fit=await cockpit.locator('.sw-grid').evaluate(grid=>({
    overflow:grid.scrollHeight-grid.clientHeight,
    trend:grid.querySelector('.sw-primary').getBoundingClientRect(),
    identity:grid.querySelector('.sw-secondary').getBoundingClientRect()
  }));
  expect(fit.overflow).toBeLessThanOrEqual(1);
  expect(fit.trend.right).toBeLessThanOrEqual(fit.identity.left+1);
  await cockpit.locator('.sw-cash-month').last().click();
  await expect(page.locator('#reportDialog')).toContainText('Published cash_flow');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail [data-sw-filter="entity"]')).toHaveCount(6);
});

test('Cash Flow shows all six entity contributions with trend and identity on a tall desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=cash-flow&page=0');
  const cockpit=page.locator('.cash-cockpit');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await expect(cockpit.locator('.sw-detail [data-sw-filter="entity"]')).toHaveCount(6);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
});

test('Cash Flow retains both visuals and KPI evidence just above the 1500px breakpoint',async({page})=>{
  await page.setViewportSize({width:1501,height:720});
  await page.goto('/#view=cash-flow&page=0');
  const cockpit=page.locator('.cash-cockpit');
  await expect(cockpit.locator('.sw-primary')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toBeVisible();
  await expect(cockpit.locator('.sw-inspector')).toBeHidden();
  await cockpit.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail [data-sw-filter="entity"]')).toHaveCount(6);
  expect(await cockpit.locator('.sw-detail').evaluate(element=>element.scrollHeight-element.clientHeight)).toBeLessThanOrEqual(1);
});
