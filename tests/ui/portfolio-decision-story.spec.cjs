const {test,expect}=require('@playwright/test');

test('portfolio story explains dated decisions and offers only months with events',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=operations-capex&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(3);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  const target=sections.find(item=>item.title.includes('Portfolio decisions'));
  expect(target).toBeTruthy();
  await page.goto(`/#view=operations-capex&page=${target.index}`);
  await expect(page.locator('.pd-visual')).toBeVisible();
  const current=await page.evaluate(()=>data.meta.end_month);
  const currentCount=await page.evaluate(()=>data.portfolio_events.filter(row=>row.month===data.meta.end_month).length);
  await expect(page.locator('.pd-card')).toHaveCount(currentCount);
  await expect(page.locator(`[data-pd-month="${current}"]`)).toHaveAttribute('aria-pressed','true');
  const other=await page.evaluate(()=>{
    const window=FinancePortfolioStory.months(data.meta.end_month);
    return [...new Set(data.portfolio_events.map(row=>row.month))].filter(month=>month!==data.meta.end_month&&window.includes(month)).at(-1);
  });
  expect(other).toBeTruthy();
  await page.locator(`[data-pd-month="${other}"]`).click();
  await expect(page.locator(`[data-pd-month="${other}"]`)).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.pd-card')).toHaveCount(await page.evaluate(month=>data.portfolio_events.filter(row=>row.month===month).length,other));
  await page.locator('.pd-source summary').click();
  await expect(page.locator('.pd-source table')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/portfolio-decision-desktop.png',fullPage:true});

  await page.setViewportSize({width:390,height:844});
  await page.goto(`/#view=operations-capex&page=${target.index}`);
  await expect(page.locator('.pd-visual')).toBeVisible();
  const sourceBounds=await page.locator('.pd-source summary').boundingBox();
  expect(sourceBounds.y+sourceBounds.height).toBeLessThan(805);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/portfolio-decision-mobile.png',fullPage:true});
});
