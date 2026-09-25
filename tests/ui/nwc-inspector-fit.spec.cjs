const {test,expect}=require('@playwright/test');

test('working capital shows complete inspector beside source evidence on a laptop',async({page},testInfo)=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=working-capital&page=0');
  await expect(page.locator('.cx-flow-map.nwc-flow-compact button')).toHaveCount(4);
  await expect(page.locator('.cx-evidence tbody tr')).toHaveCount(2);
  const geometry=await page.evaluate(()=>{
    const inspector=document.querySelector('.cx-inspector'),details=inspector.querySelector('dl');
    const evidence=document.querySelector('.cx-evidence').getBoundingClientRect();
    const side=inspector.getBoundingClientRect();
    return {details:details.clientHeight,content:details.scrollHeight,evidenceRight:evidence.right,inspectorLeft:side.left,inspectorBottom:side.bottom,evidenceBottom:evidence.bottom,overflow:document.documentElement.scrollWidth-innerWidth};
  });
  expect(geometry.content,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.details+1);
  expect(geometry.evidenceRight,JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.inspectorLeft+1);
  expect(geometry.inspectorBottom).toBeGreaterThanOrEqual(geometry.evidenceBottom-1);
  expect(geometry.overflow).toBeLessThanOrEqual(1);
  const screenshot=testInfo.outputPath('nwc-inspector-1280x720.png');
  await page.screenshot({path:screenshot});
  await testInfo.attach('nwc-inspector-1280x720',{path:screenshot,contentType:'image/png'});
  await page.locator('.cx-evidence tbody tr').first().click();
  await expect(page.locator('#reportDialog')).toBeVisible();
  await expect(page.locator('#reportDialogTitle')).toHaveText('Published source record');
});

test('source evidence rows remain keyboard-accessible on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#view=working-capital&page=0');
  await page.locator('.cx-analysis-nav').getByRole('button',{name:'Underlying records'}).click();
  const row=page.locator('.cx-evidence tbody tr').first();
  await expect(row).toBeVisible();
  await row.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#reportDialogTitle')).toHaveText('Published source record');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('the shared contribution record drill works for receivables',async({page})=>{
  await page.setViewportSize({width:1280,height:720});
  await page.goto('/#view=working-capital&page=1');
  await expect(page.locator('.cx-evidence tbody tr').first()).toBeVisible();
  await page.locator('.cx-evidence tbody tr').first().click();
  await expect(page.locator('#reportDialogTitle')).toHaveText('Published source record');
  await expect(page.locator('#reportDialogBody .row-detail')).toBeVisible();
});
