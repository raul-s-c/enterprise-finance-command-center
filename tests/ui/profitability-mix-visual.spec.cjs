const {test,expect}=require('@playwright/test');

test('family and tier mix stay source-reconciled and responsive',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=profitability&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(3);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  const target=sections.find(item=>item.title.includes('Family economics'));
  expect(target?.title).toContain('Quality-tier economics');
  await page.goto(`/#view=profitability&page=${target.index}`);
  await expect(page.locator('.pm-visual')).toHaveCount(2);
  await expect(page.locator('.pm-row')).toHaveCount(await page.evaluate(()=>Math.min(data.product_family_profitability.length,7)));
  await expect(page.locator('.pm-tier')).toHaveCount(await page.evaluate(()=>data.quality_tier_profitability.length));
  await expect(page.locator('.pm-reconcile')).toContainText('reconciled');
  await expect(page.locator('.pm-source')).toHaveCount(2);
  await page.locator('.pm-visual').first().getByRole('button',{name:'Operating contribution'}).click();
  await expect(page.locator('.pm-visual').first().getByRole('button',{name:'Operating contribution'})).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.pm-reconcile')).toContainText('reconciled');
  await page.goto(`/#view=profitability&page=${target.index}&division=Hardware`);
  await expect(page.locator('#reportContext')).toContainText('Division: Hardware');
  await expect(page.locator('.pm-tier')).toHaveCount(await page.evaluate(()=>data.quality_tier_profitability.filter(row=>row.division==='Hardware').length));
  await expect(page.locator('.pm-reconcile')).toContainText('reconciled');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/profitability-mix-desktop.png',fullPage:true});

  await page.setViewportSize({width:390,height:844});
  await page.goto(`/#view=profitability&page=${target.index}`);
  await expect(page.locator('.pm-visual')).toHaveCount(2);
  const regions=page.getByRole('navigation',{name:'Dashboard regions'});
  await expect(regions.getByRole('button')).toHaveCount(2);
  await regions.getByRole('button').nth(1).click();
  await expect(page.locator('.pm-visual').last()).toBeVisible();
  await expect(page.locator('.pm-visual').first()).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/profitability-mix-mobile.png',fullPage:true});
});
