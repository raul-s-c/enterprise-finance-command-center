const {test,expect}=require('@playwright/test');
const published=require('../../web/data/dashboard.json');

test('working-capital quality has reconciled visual evidence and accessible source schedules',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=working-capital&page=0');
  await expect(page.locator('#content')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(5);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  for(const [heading,file] of [['Expected credit loss exposure','wc-ar-quality'],['Inventory provision exposure','wc-inventory-quality']]){
    const target=sections.find(item=>item.title.includes(heading));expect(target).toBeTruthy();
    await page.goto(`/#view=working-capital&page=${target.index}`);
    await expect(page.getByText(heading,{exact:true})).toBeVisible();
    await expect(page.locator('.wq-ranked')).toBeVisible();
    await expect(page.locator('.wq-aging')).toBeVisible();
    await expect(page.locator('.wq-source')).toHaveCount(2);
    const age=page.locator('.wq-aging');
    await expect(age.locator('.wq-aging-stack i')).toHaveCount(5);
    await expect(age.locator('.wq-aging-foot')).toContainText('Buckets reconcile');
    await expect(page.locator('.wq-ranked .wq-rank')).toHaveCount(5);
    await expect(page.locator('.wq-trend polyline')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
    await page.screenshot({path:`test-results/${file}-desktop.png`,fullPage:true});
    await page.locator('.wq-source').first().locator('summary').click();
    await expect(page.locator('.wq-source').first().locator('table')).toBeVisible();
    await page.locator('.wq-source').first().locator('summary').click();
    await page.setViewportSize({width:390,height:844});
    await page.goto(`/#view=working-capital&page=${target.index}`);
    const regions=page.getByRole('navigation',{name:'Dashboard regions'});
    await expect(regions.getByRole('button')).toHaveCount(2);
    await expect(page.locator('.wq-ranked')).toBeVisible();
    await regions.getByRole('button').nth(1).click();
    await expect(page.locator('.wq-aging')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
    await page.screenshot({path:`test-results/${file}-mobile.png`,fullPage:true});
    await page.setViewportSize({width:1280,height:720});
  }
  expect(Number(published.ar_aging_summary.at(-1).total_ar)).toBeGreaterThan(0);
});
