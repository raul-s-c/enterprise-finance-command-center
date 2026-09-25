const {test,expect}=require('@playwright/test');

test('Margin shows trend and accounting bridge together on a laptop, with readable labels and reachable contribution',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=margin&page=0&entity=all&division=all');
  const cockpit=page.locator('.margin-cockpit');
  await expect(cockpit.locator('.sw-primary .sw-positive-month')).toHaveCount(12);
  await expect(cockpit.locator('.sw-secondary .horizontal-bridge')).toBeVisible();
  const fit=await cockpit.locator('.sw-grid').evaluate(grid=>{
    const bridge=grid.querySelector('.horizontal-bridge');
    const labels=[...bridge.querySelectorAll('.axis-text')];
    const bars=[...bridge.querySelectorAll('rect')];
    return {
      overflow:grid.scrollHeight-grid.clientHeight,
      trend:grid.querySelector('.sw-primary').getBoundingClientRect(),
      bridge:grid.querySelector('.sw-secondary').getBoundingClientRect(),
      lastLabel:Math.max(...labels.map(label=>label.getBBox().x+label.getBBox().width)),
      firstBar:Math.min(...bars.map(bar=>Number(bar.getAttribute('x')))),
      textSize:Math.min(...labels.map(label=>{
        const matrix=label.getScreenCTM();
        return parseFloat(getComputedStyle(label).fontSize)*Math.hypot(matrix.a,matrix.b);
      }))
    };
  });
  expect(fit.overflow).toBeLessThanOrEqual(1);
  expect(fit.trend.right).toBeLessThanOrEqual(fit.bridge.left+1);
  expect(fit.lastLabel).toBeLessThan(fit.firstBar);
  expect(fit.textSize).toBeGreaterThanOrEqual(10);
  await page.getByRole('button',{name:'Contribution & detail',exact:true}).click();
  await expect(cockpit.locator('.sw-detail')).toBeVisible();
  await expect(cockpit.locator('.sw-detail [data-sw-filter="division"]')).toHaveCount(4);
  await cockpit.locator('.sw-detail [data-sw-row="Hardware"]').click();
  await expect(page.locator('#divisionFilter')).toHaveValue('Hardware');
  await page.getByRole('button',{name:'Trend & drivers',exact:true}).click();
  await expect(page.locator('.margin-cockpit .sw-primary')).toBeVisible();
  await expect(page.locator('.margin-cockpit .sw-secondary')).toBeVisible();
});

test('Margin exposes trend, bridge and division contribution together on a taller desktop',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=margin&page=0&entity=all&division=all');
  const cockpit=page.locator('.margin-cockpit');
  for(const selector of ['.sw-primary','.sw-secondary','.sw-detail']){
    const panel=cockpit.locator(selector);
    await expect(panel).toBeVisible();
    expect(await panel.evaluate(element=>element.scrollHeight-element.clientHeight),`${selector} is clipped`).toBeLessThanOrEqual(1);
  }
  await expect(cockpit.locator('.sw-detail [data-sw-filter="division"]')).toHaveCount(4);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
});
