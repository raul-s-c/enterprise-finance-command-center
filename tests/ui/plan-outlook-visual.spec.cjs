const {test,expect}=require('@playwright/test');

test('planning vintages remain readable and interactive on desktop and mobile',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.length)).toBeGreaterThan(5);
  const sections=await page.evaluate(()=>reportState.pages.map((item,index)=>({title:item.title,index})));
  const target=sections.find(item=>item.title.includes('FY outlook evolution'));
  expect(target).toBeTruthy();
  await page.goto(`/#view=forecast&page=${target.index}`);
  await expect(page.locator('.po-ytd')).toBeVisible();
  await expect(page.locator('[data-po-ytd-month]')).toHaveCount(await page.evaluate(()=>new Set(data.budget_performance.map(row=>row.month)).size));
  const firstMonth=await page.locator('[data-po-ytd-month]').first().getAttribute('data-po-ytd-month');
  await page.locator('[data-po-ytd-month]').first().click();
  await expect(page.locator('.po-ytd-selected')).toContainText(firstMonth);
  const ytdSource=page.locator('.po-ytd + .po-source summary');
  await expect(ytdSource).toBeVisible();
  const ytdSourceBounds=await ytdSource.boundingBox();
  expect(ytdSourceBounds.y+ytdSourceBounds.height).toBeLessThan(680);
  await page.locator('[data-po-ytd-metric="ebit"]').click();
  await expect(page.locator('[data-po-ytd-metric="ebit"]')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.po-visual')).toBeVisible();
  await expect(page.locator('.po-row')).toHaveCount(5);
  await page.locator('[data-po-metric="ebit"]').click();
  await expect(page.locator('[data-po-metric="ebit"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('.po-visual + .po-source summary').click();
  await expect(page.locator('.po-visual + .po-source')).toHaveAttribute('open','');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/plan-outlook-desktop.png',fullPage:true});

  await page.setViewportSize({width:768,height:720});
  await page.goto(`/#view=forecast&page=${target.index}`);
  await page.reload();
  await expect(page.locator('.po-ytd')).toBeVisible();
  const laptopSource=await page.locator('.po-source summary').first().boundingBox();
  expect(laptopSource.y+laptopSource.height).toBeLessThan(680);
  await page.getByRole('navigation',{name:'Dashboard regions'}).getByRole('button',{name:/FY outlook evolution/}).click();
  await expect(page.locator('.po-visual')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/plan-outlook-laptop.png',fullPage:true});

  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=forecast&page=0');
  await page.reload();
  await expect.poll(()=>page.evaluate(()=>reportState.pages.some(item=>item.title.includes('FY outlook evolution')))).toBe(true);
  const mobileTarget=await page.evaluate(()=>reportState.pages.findIndex(item=>item.title.includes('FY outlook evolution')));
  expect(mobileTarget).toBeGreaterThan(0);
  await page.goto(`/#view=forecast&page=${mobileTarget}`);
  await expect(page.locator('.po-ytd')).toBeVisible();
  await expect(page.locator('[data-po-ytd-month]')).toHaveCount(await page.evaluate(()=>new Set(data.budget_performance.map(row=>row.month)).size));
  const mobileSource=await page.locator('.po-ytd + .po-source summary').boundingBox();
  expect(mobileSource.y+mobileSource.height).toBeLessThan(805);
  await page.screenshot({path:'test-results/plan-ytd-mobile.png',fullPage:true});
  await page.getByRole('navigation',{name:'Dashboard regions'}).getByRole('button',{name:/FY outlook evolution/}).click();
  await expect(page.locator('.po-visual')).toBeVisible();
  await expect(page.locator('.po-row')).toHaveCount(5);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'test-results/plan-outlook-mobile.png',fullPage:true});
});

test('revenue-free cost center shows EBIT rather than a blank planning chart',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=forecast&page=0');
  await expect.poll(()=>page.evaluate(()=>reportState.pages.some(item=>item.title.includes('FY outlook evolution')))).toBe(true);
  const center=await page.evaluate(()=>{
    const row=data.fy_plan_bridge.find(item=>['fy_budget_revenue','fc_6_fy_revenue','fc_3_fy_revenue','fc_1_fy_revenue','latest_fy_revenue'].every(key=>Number(item[key])===0)&&Number(item.latest_fy_ebit)!==0);
    return {entity:row.entity,division:row.division};
  });
  const target=await page.evaluate(()=>reportState.pages.findIndex(item=>item.title.includes('FY outlook evolution')));
  await page.goto(`/#view=forecast&page=${target}&entity=${encodeURIComponent(center.entity)}&division=${encodeURIComponent(center.division)}`);
  await expect(page.locator('.po-ytd')).toContainText('cost center: no revenue');
  await expect(page.locator('.po-visual')).toContainText('cost center: no revenue');
  await expect(page.locator('[data-po-metric="revenue"]')).toBeDisabled();
  await expect(page.locator('[data-po-ytd-metric="revenue"]')).toBeDisabled();
  await expect(page.locator('[data-po-metric="ebit"]')).toHaveAttribute('aria-pressed','true');
});
