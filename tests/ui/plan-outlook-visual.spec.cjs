const {test,expect}=require('@playwright/test');

test('planning vintages remain readable and interactive on desktop and mobile',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(5);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  const target=sections.find(item=>item.title.includes('FY outlook evolution'));
  expect(target).toBeTruthy();
  await page.goto(`/#view=forecast&page=${target.index}`);
  await expect(page.locator('.po-visual')).toBeVisible();
  await expect(page.locator('.po-row')).toHaveCount(5);
  await page.locator('[data-po-metric="ebit"]').click();
  await expect(page.locator('[data-po-metric="ebit"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('.po-source summary').click();
  await expect(page.locator('.po-source')).toHaveAttribute('open','');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/plan-outlook-desktop.png',fullPage:true});

  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=forecast&page=0');
  const mobileTarget=await page.evaluate(()=>reportState.pages.findIndex(item=>item.title.includes('FY outlook evolution')));
  expect(mobileTarget).toBeGreaterThan(0);
  await page.goto(`/#view=forecast&page=${mobileTarget}`);
  await page.getByRole('navigation',{name:'Dashboard regions'}).getByRole('button',{name:/FY outlook evolution/}).click();
  await expect(page.locator('.po-visual')).toBeVisible();
  await expect(page.locator('.po-row')).toHaveCount(5);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/plan-outlook-mobile.png',fullPage:true});
});
