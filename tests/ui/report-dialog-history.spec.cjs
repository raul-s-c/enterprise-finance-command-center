const {test,expect}=require('@playwright/test');

test('browser history closes a source dialog before showing another report',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=working-capital&page=0');
  await page.locator('.cx-evidence tbody tr').first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();

  await page.evaluate(()=>{location.hash='#view=pnl&page=0';});
  await expect(page.locator('#reportDialog')).toBeHidden();
  await expect(page.locator('#viewTitle')).toContainText('P&L');

  await page.goBack();
  await expect(page.locator('.contribution-explorer[data-contribution="nwc"]')).toBeVisible();
  await expect(page.locator('#reportDialog')).toBeHidden();

  await page.getByRole('button',{name:'Help'}).first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await page.goForward();
  await expect(page.locator('#reportDialog')).toBeHidden();
  await expect(page.locator('#viewTitle')).toContainText('P&L');
});
