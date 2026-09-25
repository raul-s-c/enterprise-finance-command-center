const {test,expect}=require('@playwright/test');

test('OPEX detail becomes a source-tied mix, trend and division visual',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=pnl&page=4');
  const panel=page.locator('.ox-panel');
  await expect(panel).toBeVisible();
  await expect(panel.locator('.ox-trend button')).toHaveCount(12);
  await expect(panel.locator('.ox-division')).toHaveCount(4);
  await expect(panel.locator('.ox-check')).toContainText('reconciled');
  await expect(panel.locator('.ox-headline strong').first()).toContainText('€4.3m');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth||document.documentElement.scrollHeight>innerHeight)).toBe(false);
  const selected=await panel.locator('.ox-selected').boundingBox();
  const source=await panel.locator('.ox-source summary').boundingBox();
  const footer=await page.locator('.report-footer').boundingBox();
  expect(selected.y+selected.height).toBeLessThan(source.y);
  expect(source.y+source.height).toBeLessThan(footer.y);
  await page.screenshot({path:'test-results/opex-desktop.png'});

  const previous=await page.evaluate(()=>data.actual.at(-2).month);
  await panel.locator(`[data-ox-month="${previous}"]`).click();
  await expect(panel.locator(`[data-ox-month="${previous}"]`)).toHaveAttribute('aria-pressed','true');
  await expect(panel.locator('.ox-selected')).toContainText(previous);
  await panel.locator('.ox-source summary').click();
  await expect(panel.locator('.ox-source table tbody tr')).toHaveCount(12);
  await expect(panel.locator('.ox-source')).toContainText('not an invoice allocation');

  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=pnl&page=4');
  await expect(panel).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  expect(await panel.evaluate(node=>getComputedStyle(node).overflowY)).toBe('auto');
  expect(await panel.evaluate(node=>node.scrollHeight>node.clientHeight)).toBe(true);
  await panel.evaluate(node=>node.scrollTo({top:node.scrollHeight,behavior:'instant'}));
  await expect.poll(()=>panel.evaluate(node=>node.scrollHeight-node.clientHeight-node.scrollTop)).toBeLessThan(2);
  const reach=await panel.evaluate(node=>({source:node.querySelector('.ox-source summary').getBoundingClientRect().bottom,panel:node.getBoundingClientRect().bottom}));
  expect(reach.source).toBeLessThanOrEqual(reach.panel+2);
  await page.screenshot({path:'test-results/opex-mobile.png',fullPage:true});
});
