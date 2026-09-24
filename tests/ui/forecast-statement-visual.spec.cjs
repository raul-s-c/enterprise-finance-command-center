const {test,expect}=require('@playwright/test');

test('scenario and group workforce forecast remain legible and source-tied at laptop and mobile widths',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(4);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  const target=sections.find(item=>item.title.includes('Integrated three-statement scenarios'));
  expect(target?.title).toContain('Base workforce plan');
  await page.goto(`/#view=forecast&page=${target.index}&entity=US01&division=Hardware`);
  await expect(page.locator('.fs-visual')).toHaveCount(2);
  await expect(page.locator('.fs-scenario')).toHaveCount(3);
  await expect(page.locator('.fs-source')).toHaveCount(2);
  await expect(page.locator('#reportContext')).toContainText('Group');
  const expected=await page.evaluate(()=>{
    const base=data.three_statement_forecast_summary.find(row=>row.scenario==='Base');
    return {ebit:`€${(base.ebit_12m/1e6).toFixed(1)}m`,fcf:`€${(base.free_cash_flow_12m/1e6).toFixed(1)}m`};
  });
  await expect(page.locator('.fs-scenario.base b')).toContainText(expected.ebit);
  await page.getByRole('button',{name:'Free cash flow',exact:true}).click();
  await expect(page.locator('.fs-scenario.base b')).toContainText(expected.fcf);
  await expect(page.getByRole('button',{name:'Free cash flow',exact:true})).toHaveAttribute('aria-pressed','true');
  await page.locator('.fs-source').first().locator('summary').click();
  await expect(page.locator('.fs-source').first().locator('table')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/forecast-statement-desktop.png',fullPage:true});

  await page.setViewportSize({width:390,height:844});
  await page.goto(`/#view=forecast&page=${target.index}`);
  await expect(page.locator('.fs-visual')).toHaveCount(2);
  const regions=page.getByRole('navigation',{name:'Dashboard regions'});
  await expect(regions.getByRole('button')).toHaveCount(2);
  await regions.getByRole('button').nth(1).click();
  await expect(page.locator('.fs-visual').last()).toBeVisible();
  await expect(page.locator('.fs-visual').first()).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/forecast-statement-mobile.png',fullPage:true});
});
