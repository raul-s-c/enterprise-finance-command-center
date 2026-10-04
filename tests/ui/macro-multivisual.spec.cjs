const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('Macro keeps eight independent shock impacts beside the EBIT identity on a laptop',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=macro-sensitivities&page=0');
  const cockpit=page.locator('.macro-cockpit');
  await expect(cockpit.locator('.sw-primary .sw-ranking button')).toHaveCount(8);
  await expect(cockpit.locator('.sw-secondary .sw-formula')).toBeVisible();
  await expect(cockpit.locator('.sw-primary')).toContainText('scenarios must never be added');
  for(const selector of ['.sw-primary','.sw-secondary']){
    expect(await cockpit.locator(selector).evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await cockpit.locator('.sw-primary [data-sw-row="Price +1%"]').click();
  await expect(cockpit.locator('.sw-secondary')).toContainText('Price +1%');
  const priceImpact=published.financial_sensitivity_detail.filter(row=>row.shock==='Price +1%').reduce((sum,row)=>sum+Number(row.gross_profit_impact||0),0);
  expect(priceImpact).toBeGreaterThan(0);
  const displayed=`€${(priceImpact/1e6).toLocaleString('en-US',{minimumFractionDigits:1,maximumFractionDigits:1})}m`;
  await expect(cockpit.locator('.sw-secondary .sw-formula')).toContainText(displayed);
  await expect(page.locator('#reportDialog')).toContainText('financial_sensitivity_detail');
  await page.locator('#reportDialogClose').click();
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail .sw-ranking button')).toHaveCount(8);
});

test('Macro shows exposure and source coverage together on a tall desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=macro-sensitivities&page=0');
  const cockpit=page.locator('.macro-cockpit');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await expect(cockpit.locator('.sw-detail')).toContainText('Official-source coverage');
});

test('Macro retains KPI evidence at the short-window desktop breakpoint',async({page})=>{
  await page.setViewportSize({width:1501,height:720});
  await page.goto('/#view=macro-sensitivities&page=0');
  const cockpit=page.locator('.macro-cockpit');
  await expect(cockpit.locator('.sw-primary')).toBeVisible();
  await expect(cockpit.locator('.sw-secondary')).toBeVisible();
  await expect(cockpit.locator('.sw-inspector')).toBeHidden();
  await cockpit.locator('.sw-kpi').first().click();
  await expect(page.locator('#reportDialog')).toContainText('Calculation');
  await page.locator('#reportDialogClose').click();
});
