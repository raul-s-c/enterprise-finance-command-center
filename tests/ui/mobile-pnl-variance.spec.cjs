const {test,expect}=require('@playwright/test');

test('mobile P&L exposes both actuals and signed variances without sideways scrolling',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=pnl&page=0');
  await expect(page.locator('[data-pnl-key]')).toHaveCount(10);
  const statement=page.locator('.pnl-visual');
  const controls=page.getByRole('group',{name:'Mobile P&L columns'});
  await expect(controls).toBeVisible();
  await expect(controls.getByRole('button',{name:'Values'})).toHaveAttribute('aria-pressed','true');
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeVisible();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeHidden();
  await controls.getByRole('button',{name:'Δ PY'}).click();
  await expect(controls.getByRole('button',{name:'Δ PY'})).toHaveAttribute('aria-pressed','true');
  await expect(statement.locator('.pnl-variance-context')).toBeVisible();
  await expect(statement.locator('.pnl-variance-context')).toContainText('green = favorable, red = adverse');
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeHidden();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeVisible();
  await expect(statement.locator('[data-pnl-key="revenue"] .pnl-delta')).toBeVisible();
  await expect(statement.locator('[data-pnl-key="revenue"] .pnl-percent')).toBeVisible();
  expect(await statement.locator('.pnl-scroll').evaluate(node=>node.scrollWidth>node.clientWidth+1)).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  const last=await statement.locator('[data-pnl-key]').last().boundingBox();
  const footer=await page.locator('.report-footer').boundingBox();
  expect(last.y+last.height).toBeLessThanOrEqual(footer.y);
  await page.screenshot({path:'test-results/mobile-pnl-variance.png'});
  await controls.getByRole('button',{name:'Values'}).click();
  await expect(statement.locator('.pnl-heading>span:nth-child(2)')).toBeVisible();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeHidden();

  await page.setViewportSize({width:1280,height:720});
  await expect(controls).toBeHidden();
  await expect(statement.locator('.pnl-heading>span:nth-child(4)')).toBeVisible();
});
