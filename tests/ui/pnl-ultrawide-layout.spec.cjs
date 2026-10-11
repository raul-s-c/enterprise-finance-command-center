const {test,expect}=require('@playwright/test');

test('ultrawide P&L keeps the statement and evidence inspector visually grouped',async({page})=>{
  await page.setViewportSize({width:2560,height:1440});
  await page.goto('/#view=pnl&page=0');
  const layout=page.locator('.pnl-analysis-layout');
  await expect(layout).toBeVisible();
  await expect(layout.locator('.pnl-inline-inspector')).toBeVisible();
  await expect(page.locator('.pnl-row')).toHaveCount(10);
  const geometry=await layout.evaluate(element=>{
    const bounds=element.getBoundingClientRect();
    const statement=element.querySelector('.pnl-visual').getBoundingClientRect();
    const inspector=element.querySelector('.pnl-inline-inspector').getBoundingClientRect();
    const row=element.querySelector('.pnl-row');
    return {
      statementWidth:statement.width,
      combinedWidth:inspector.right-statement.left,
      centerOffset:Math.abs((statement.left+inspector.right)/2-(bounds.left+bounds.right)/2),
      gap:inspector.left-statement.right,
      documentOverflow:document.documentElement.scrollWidth>innerWidth+1,
      labelFont:parseFloat(getComputedStyle(row.querySelector('span')).fontSize),
      varianceFont:parseFloat(getComputedStyle(row.querySelector('.pnl-delta b')).fontSize)
    };
  });
  expect(geometry.statementWidth).toBeGreaterThan(1500);
  expect(geometry.statementWidth).toBeLessThanOrEqual(1801);
  expect(geometry.combinedWidth).toBeLessThanOrEqual(2113);
  expect(geometry.centerOffset).toBeLessThanOrEqual(3);
  expect(geometry.gap).toBeGreaterThanOrEqual(0);
  expect(geometry.gap).toBeLessThanOrEqual(13);
  expect(geometry.documentOverflow).toBe(false);
  expect(geometry.labelFont).toBeGreaterThanOrEqual(14);
  expect(geometry.varianceFont).toBeGreaterThanOrEqual(14);

  await page.locator('[data-pnl-key="opex"]').click();
  await expect(layout.locator('.pnl-inline-inspector')).toContainText('Sum of OPEX');
  for(const [width,height] of [[1920,1080],[1440,900],[1366,768],[390,844]]){
    await page.setViewportSize({width,height});
    await page.waitForTimeout(180);
    await expect(page.locator('.pnl-row')).toHaveCount(10);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),"P&L document overflows at "+width+"×"+height).toBe(true);
  }
});
