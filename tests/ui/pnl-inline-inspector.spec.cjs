const {test,expect}=require('@playwright/test');

test('P&L line selection updates an adjacent source inspector without hiding the statement',async({page},testInfo)=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/#view=pnl&page=0&entity=all&division=all');
  const inspector=page.locator('#pnlInlineInspector');
  await expect(inspector).toBeVisible();
  await expect(inspector.getByRole('heading',{name:'Revenue'})).toBeVisible();
  await page.locator('[data-pnl-key="ebit"]').click();
  await expect(inspector.getByRole('heading',{name:'EBIT'})).toBeVisible();
  await expect(page.locator('[data-pnl-key="ebit"]')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#reportDialog')).not.toBeVisible();
  const geometry=await page.evaluate(()=>{
    const table=document.querySelector('.pnl-visual').getBoundingClientRect();
    const aside=document.querySelector('#pnlInlineInspector').getBoundingClientRect();
    return {tableRight:table.right,asideLeft:aside.left,asideBottom:aside.bottom,viewportHeight:innerHeight,overflow:document.documentElement.scrollWidth-innerWidth};
  });
  expect(geometry.tableRight,JSON.stringify(geometry)).toBeLessThan(geometry.asideLeft);
  expect(geometry.asideBottom,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.viewportHeight);
  expect(geometry.overflow,JSON.stringify(geometry)).toBeLessThanOrEqual(1);
  const screenshot=testInfo.outputPath('pnl-inline-inspector-1440.png');
  await page.screenshot({path:screenshot});
  await testInfo.attach('pnl-inline-inspector-1440',{path:screenshot,contentType:'image/png'});
  await inspector.getByRole('button',{name:/Open full EBIT evidence/}).click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await expect(page.locator('.pnl-source-detail')).toBeVisible();
});

test('P&L retains full-width statement and evidence dialog on a laptop',async({page})=>{
  await page.setViewportSize({width:1024,height:768});
  await page.goto('/#view=pnl&page=0&entity=all&division=all');
  await expect(page.locator('#pnlInlineInspector')).toBeHidden();
  await expect(page.locator('[data-pnl-key="net_income"]')).toBeInViewport();
  await page.locator('[data-pnl-key="ebit"]').click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
